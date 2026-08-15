import os
import sys
# pyrefly: ignore [missing-import]
import joblib
# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
import torch.nn as nn
# pyrefly: ignore [missing-import]
from torch.utils.data import DataLoader, TensorDataset
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.sequence import SequenceBuilder, FEATURE_COLS

class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features, hidden_dim=64, n_layers=2, dropout=0.2):
        super().__init__()
        
        # Encoder: compress sequence into bottleneck state
        self.encoder = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0
        )
        
        # Bottleneck representational layer
        self.bottleneck = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # Decoder: reconstruct sequence back to full dim
        self.decoder = nn.LSTM(
            input_size=hidden_dim // 2,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0
        )
        
        self.output_layer = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        # x shape: (batch, seq_len, n_features)
        _, (hidden, _) = self.encoder(x)
        # Take hidden state of last LSTM layer: hidden[-1]
        bottleneck = self.bottleneck(hidden[-1]) # shape: (batch, hidden_dim // 2)
        
        # Repeat bottleneck state for each timestep of sequence
        bottleneck_seq = bottleneck.unsqueeze(1).repeat(1, x.size(1), 1) # shape: (batch, seq_len, hidden_dim // 2)
        
        decoded, _ = self.decoder(bottleneck_seq)
        return self.output_layer(decoded)

    def reconstruction_error(self, x):
        self.eval()
        with torch.no_grad():
            x_hat = self.forward(x)
            # MSE per sample across timesteps and features
            return torch.mean((x - x_hat) ** 2, dim=(1, 2))

def train_model():
    print("[Model A1] Starting Anomaly Detection LSTM Autoencoder training...")
    
    DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
    DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
    DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
    DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
    DB_NAME = "astra_predictive_maintenance"
    
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    
    # Query normal data for motor MTR-01 (Conveyor healthy data source)
    query = "SELECT * FROM feature_windows WHERE motor_id = 'MTR-01' ORDER BY window_end ASC"
    df = pd.read_sql(query, engine)
    
    if len(df) < 20:
        print(f"[Model A1] Insufficient data. Found {len(df)} feature windows for MTR-01, need at least 20.")
        return
        
    print(f"[Model A1] Loaded {len(df)} feature windows for MTR-01.")
    
    # Build sequences
    seq_builder = SequenceBuilder(scaler_dir='models')
    
    # Fit scaler on MTR-01 training set
    sequences = []
    n_windows = len(df)
    for i in range(n_windows - 20 + 1):
        window_subset = df.iloc[i:i+20]
        # Fit scaler on the very first chunk
        fit = (i == 0)
        seq = seq_builder.build_sequence(window_subset, 'MTR-01', fit_scaler=fit)
        sequences.append(seq)
        
    sequences = np.array(sequences, dtype=np.float32)
    print(f"[Model A1] Built {len(sequences)} normal sequences. Shape: {sequences.shape}")
    
    # Chronological Split: 70% train, 15% val, 15% test
    n = len(sequences)
    train_idx = int(n * 0.70)
    val_idx = int(n * 0.85)
    
    train_seqs = torch.tensor(sequences[:train_idx])
    val_seqs = torch.tensor(sequences[train_idx:val_idx])
    test_seqs = torch.tensor(sequences[val_idx:])
    
    print(f"[Model A1] Splits: Train={len(train_seqs)}, Val={len(val_seqs)}, Test={len(test_seqs)}")
    
    train_loader = DataLoader(TensorDataset(train_seqs), batch_size=32, shuffle=False)
    
    # Model config
    n_features = sequences.shape[2]
    model = LSTMAutoencoder(n_features=n_features, hidden_dim=64, n_layers=2, dropout=0.2)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    # Training Loop
    epochs = 40
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            x = batch[0]
            optimizer.zero_grad()
            x_hat = model(x)
            loss = criterion(x_hat, x)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x.size(0)
            
        train_loss /= len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for val_batch in DataLoader(TensorDataset(val_seqs), batch_size=32):
                x_val = val_batch[0]
                x_val_hat = model(x_val)
                loss_val = criterion(x_val_hat, x_val)
                val_loss += loss_val.item() * x_val.size(0)
        val_loss /= len(val_seqs)
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"[Model A1] Epoch {epoch+1:02d}/{epochs} | Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f}")
            
    # Calculate anomaly threshold from validation set reconstruction errors
    # 97th percentile of normal validation reconstruction errors
    val_errors = model.reconstruction_error(val_seqs)
    threshold = float(np.percentile(val_errors.numpy(), 97))
    print(f"[Model A1] Anomaly Threshold (97th percentile): {threshold:.6f}")
    
    # Evaluate on test set
    test_errors = model.reconstruction_error(test_seqs)
    false_positives = torch.sum(test_errors > threshold).item()
    fpr = false_positives / len(test_errors) * 100
    print(f"[Model A1] Evaluation on test set: False Positive Rate = {fpr:.2f}% (Target: < 15%)")
    
    # Save Model & Metadata
    os.makedirs('models', exist_ok=True)
    torch.save(model.state_dict(), 'models/model_a1_v1.pt')
    joblib.dump({'threshold': threshold, 'n_features': n_features}, 'models/anomaly_meta.pkl')
    print("[Model A1] Saved weights to 'models/model_a1_v1.pt' and metadata to 'models/anomaly_meta.pkl'.")

if __name__ == '__main__':
    train_model()
