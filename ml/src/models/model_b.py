import os
import sys
# pyrefly: ignore [missing-import]
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.sequence import FEATURE_COLS

class RULPredictor(nn.Module):
    def __init__(self, n_features, hidden_dim=128, n_layers=2):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=0.3 if n_layers > 1 else 0.0,
            bidirectional=False # Unidirectional only
        )
        
        # Regression head
        self.regressor = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1)
        )

    def forward(self, x):
        # x shape: (batch, seq_len, n_features)
        lstm_out, _ = self.lstm(x)
        # Take the output of the last timestep
        last_out = lstm_out[:, -1, :] # shape: (batch, hidden_dim)
        return self.regressor(last_out).squeeze()

def load_cmapss_sequences(filepath, seq_len=120):
    """
    Reads the raw CMAPSS train file, computes RUL, scales features, 
    and builds sliding window sequences of length seq_len.
    """
    cols = ['engine_id', 'cycle', 'setting1', 'setting2', 'setting3'] + [f's{i}' for i in range(1, 22)]
    df = pd.read_csv(filepath, sep=r'\s+', header=None, names=cols)
    
    # We will map CMAPSS features to match ASTRA's FEATURE_COLS layout!
    # ASTRA expects 25 features. Let's populate them from CMAPSS parameters:
    # ASTRA feature columns:
    #   'temp_mean', 'temp_max', 'temp_min', 'temp_slope', 'temp_std',
    #   'vib_rms', 'vib_peak', 'vib_kurtosis', 'vib_skewness', 'vib_crest',
    #   'vib_fft_low', 'vib_fft_high',
    #   'current_mean', 'current_std', 'current_thd', 'current_slope',
    #   'rpm_mean', 'rpm_std', 'rpm_drop_pct',
    #   'torque_mean', 'torque_std', 'torque_peak',
    #   'load_ratio', 'temp_per_load', 'power_estimate'
    
    # Map CMAPSS fields to our 25 feature columns
    mapped_df = pd.DataFrame(index=df.index)
    
    # Temperature (s2)
    mapped_df['temp_mean'] = df['s2']
    mapped_df['temp_max'] = df['s2'] + 2.0
    mapped_df['temp_min'] = df['s2'] - 2.0
    mapped_df['temp_slope'] = 0.05
    mapped_df['temp_std'] = 1.2
    
    # Vibration (s6 is vibration proxy)
    mapped_df['vib_rms'] = df['s6']
    mapped_df['vib_peak'] = df['s6'] * 1.414
    mapped_df['vib_kurtosis'] = 3.0
    mapped_df['vib_skewness'] = 0.0
    mapped_df['vib_crest'] = 1.414
    mapped_df['vib_fft_low'] = df['s6'] * 50.0
    mapped_df['vib_fft_high'] = df['s6'] * 10.0
    
    # Current (s12 is current proxy)
    mapped_df['current_mean'] = df['s12']
    mapped_df['current_std'] = 0.2
    mapped_df['current_thd'] = 0.02
    mapped_df['current_slope'] = 0.001
    
    # RPM (s11 is RPM)
    mapped_df['rpm_mean'] = df['s11']
    mapped_df['rpm_std'] = 2.0
    # Nominal mixer RPM is 980
    mapped_df['rpm_drop_pct'] = np.clip((980.0 - df['s11']) / 980.0 * 100.0, 0, 100)
    
    # Torque (s13 is torque proxy)
    mapped_df['torque_mean'] = df['s13']
    mapped_df['torque_std'] = 0.5
    mapped_df['torque_peak'] = df['s13'] + 1.0
    
    # Cross parameters
    mapped_df['load_ratio'] = mapped_df['current_mean'] / (mapped_df['rpm_mean'] + 1e-8)
    mapped_df['temp_per_load'] = mapped_df['temp_mean'] / (mapped_df['current_mean'] + 1e-8)
    mapped_df['power_estimate'] = mapped_df['rpm_mean'] * mapped_df['torque_mean']
    
    df_features = mapped_df[FEATURE_COLS].copy()
    
    # Calculate RUL per engine
    # RUL = max_cycle_for_this_engine - current_cycle
    max_cycles = df.groupby('engine_id')['cycle'].max().to_dict()
    df['max_cycle'] = df['engine_id'].map(max_cycles)
    df['RUL'] = df['max_cycle'] - df['cycle']
    
    # Clip RUL at 125 as specified
    df['RUL'] = np.clip(df['RUL'], 0, 125)
    
    # Normalize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df_features.values)
    
    # Save the scaler for MTR-05
    os.makedirs('models', exist_ok=True)
    joblib.dump(scaler, 'models/scaler_MTR-05.pkl')
    print("[Model B] Saved scaler to 'models/scaler_MTR-05.pkl'")
    
    # Build sequences per engine to avoid mixing engine boundaries
    seq_list = []
    rul_list = []
    
    for eng_id in df['engine_id'].unique():
        eng_mask = df['engine_id'] == eng_id
        eng_feats = scaled_features[eng_mask]
        eng_ruls = df.loc[eng_mask, 'RUL'].values
        
        n_samples = len(eng_feats)
        for i in range(n_samples - seq_len + 1):
            seq_list.append(eng_feats[i:i+seq_len])
            # The label is the RUL at the end of the sequence window
            rul_list.append(eng_ruls[i+seq_len-1])
            
    return np.array(seq_list, dtype=np.float32), np.array(rul_list, dtype=np.float32)

def asymmetric_loss(pred, true):
    """
    Custom asymmetric loss:
    If predicted RUL is greater than true RUL (late prediction) -> penalty 2x.
    If predicted RUL is less than true RUL (early prediction) -> standard penalty.
    """
    diff = pred - true
    penalty = torch.where(diff > 0, 2.0 * (diff**2), diff**2)
    return penalty.mean()

def train_model():
    print("[Model B] Starting RUL Prediction LSTM model training...")
    
    # Find dataset path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    train_path = os.path.abspath(os.path.join(script_dir, "..", "..", "dataset", "CMaps", "train_FD001.txt"))
    
    if not os.path.exists(train_path):
        print(f"[Model B] Error: train_FD001.txt not found at {train_path}. Generating synthetic data to train...")
        # Fallback synthetic training data creation
        X_train = np.random.normal(0, 1, (1000, 120, len(FEATURE_COLS))).astype(np.float32)
        y_train = np.random.uniform(0, 125, 1000).astype(np.float32)
        X_val = np.random.normal(0, 1, (200, 120, len(FEATURE_COLS))).astype(np.float32)
        y_val = np.random.uniform(0, 125, 200).astype(np.float32)
    else:
        # Load and build sequences
        X, y = load_cmapss_sequences(train_path)
        print(f"[Model B] Loaded {len(X)} sequences from train_FD001.txt. Shape: {X.shape}")
        
        # Chronological split
        n = len(X)
        train_idx = int(n * 0.8)
        X_train, y_train = X[:train_idx], y[:train_idx]
        X_val, y_val = X[train_idx:], y[train_idx:]
        
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train), torch.tensor(y_train)), batch_size=64, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_val), torch.tensor(y_val)), batch_size=64, shuffle=False)
    
    model = RULPredictor(n_features=len(FEATURE_COLS), hidden_dim=128, n_layers=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    
    epochs = 40
    best_val_mae = float('inf')
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            pred = model(batch_x)
            loss = asymmetric_loss(pred, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss /= len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_mae = 0.0
        val_loss = 0.0
        with torch.no_grad():
            for batch_vx, batch_vy in val_loader:
                pred_v = model(batch_vx)
                loss_v = asymmetric_loss(pred_v, batch_vy)
                val_loss += loss_v.item() * batch_vx.size(0)
                val_mae += torch.abs(pred_v - batch_vy).sum().item()
                
        val_loss /= len(val_loader.dataset)
        val_mae /= len(val_loader.dataset)
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"[Model B] Epoch {epoch+1:02d}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val MAE: {val_mae:.2f}")
            
        if val_mae < best_val_mae:
            best_val_mae = val_mae
            # Save best model
            torch.save(model.state_dict(), 'models/model_b_v1.pt')
            
    print(f"[Model B] Training Complete. Best Validation MAE: {best_val_mae:.2f} (Target: < 10)")

if __name__ == '__main__':
    train_model()
