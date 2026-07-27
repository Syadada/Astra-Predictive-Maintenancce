import os
import sys
import numpy as np
import torch
import joblib
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error, mean_squared_error, f1_score

# Set path relative to ml/
PROJECT_ROOT = r"c:\Users\rasyaad\Downloads\PredictaGuard-main\PredictaGuard-main"
sys.path.append(os.path.join(PROJECT_ROOT, "ml"))

from src.models.model_a1 import LSTMAutoencoder
from src.models.model_b import RULPredictor
from src.pipeline.sequence import SequenceBuilder, FEATURE_COLS

DATA_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "ml", "models")

DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
DB_NAME = "astra_predictive_maintenance"

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def evaluate_model_a1():
    print("\n=== EVALUATING MODEL A1: LSTM AUTOENCODER (ANOMALY) ===")
    model_path = os.path.join(MODELS_DIR, "model_a1_v1.pt")
    meta_path = os.path.join(MODELS_DIR, "anomaly_meta.pkl")
    
    if not (os.path.exists(model_path) and os.path.exists(meta_path)):
        print("Model A1 weights or meta files missing.")
        return
        
    meta = joblib.load(meta_path)
    threshold = meta["threshold"]
    n_features = meta.get("n_features", len(FEATURE_COLS))
    
    # Query database for MTR-01
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM feature_windows WHERE motor_id = 'MTR-01' ORDER BY window_end ASC", conn)
        
    if len(df) < 20:
        print(f"Insufficient MTR-01 feature windows ({len(df)}/20) to run evaluation.")
        return
        
    # Build sequences
    seq_builder = SequenceBuilder(scaler_dir=MODELS_DIR)
    sequences = []
    for i in range(len(df) - 20 + 1):
        window_subset = df.iloc[i:i+20]
        seq = seq_builder.build_sequence(window_subset, 'MTR-01', fit_scaler=False)
        sequences.append(seq)
        
    X_test = np.array(sequences, dtype=np.float32)
    
    # Init model
    model = LSTMAutoencoder(n_features=n_features)
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
    
    with torch.no_grad():
        x_tensor = torch.tensor(X_test, dtype=torch.float32)
        errors = model.reconstruction_error(x_tensor).numpy()
        preds = (errors > threshold).astype(int)
        
    print(f"Test Sequences Evaluated: {len(X_test)}")
    print(f"Anomaly Threshold: {threshold:.6f}")
    print(f"Average Reconstruction Error: {np.mean(errors):.6f}")
    print(f"Max Reconstruction Error: {np.max(errors):.6f}")
    print(f"Anomaly Alarms Triggered: {np.sum(preds)} / {len(preds)} (FPR = {np.mean(preds)*100:.2f}%)")

def evaluate_model_a2():
    print("\n=== EVALUATING MODEL A2: FAULT CLASSIFIER (GBDT) ===")
    model_path = os.path.join(MODELS_DIR, "model_a2_v1.pkl")
    le_path = os.path.join(MODELS_DIR, "label_encoder_a2.pkl")
    
    if not (os.path.exists(model_path) and os.path.exists(le_path)):
        print("Model A2 files missing.")
        return
        
    model = joblib.load(model_path)
    le = joblib.load(le_path)
    
    # Query feature windows for the bearing motors (MTR-01, MTR-02, MTR-03, MTR-06)
    query = """
        SELECT * FROM feature_windows 
        WHERE motor_id IN ('MTR-01', 'MTR-02', 'MTR-03', 'MTR-06') 
        ORDER BY window_end ASC
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    if len(df) == 0:
        print("No database records found in feature_windows for classification evaluation.")
        return
        
    # Map motor_id to class label
    label_map = {
        'MTR-01': 'healthy',
        'MTR-02': 'outer_race',
        'MTR-03': 'inner_race',
        'MTR-06': 'roller'
    }
    df['fault_type'] = df['motor_id'].map(label_map)
    df_clean = df.dropna(subset=FEATURE_COLS).copy()
    
    X = df_clean[FEATURE_COLS].values
    y = df_clean['fault_type'].values
    y_encoded = le.transform(y)
    
    # Get last 20% of each motor's windows as test set
    test_indices = []
    for motor in ['MTR-01', 'MTR-02', 'MTR-03', 'MTR-06']:
        motor_idx = df_clean[df_clean['motor_id'] == motor].index.tolist()
        split_point = int(len(motor_idx) * 0.8)
        test_indices.extend(motor_idx[split_point:])
        
    df_clean['original_index'] = range(len(df_clean))
    test_arr_idx = df_clean.loc[test_indices, 'original_index'].values
    
    X_test, y_test = X[test_arr_idx], y_encoded[test_arr_idx]
    
    preds = model.predict(X_test)
    
    acc = accuracy_score(y_test, preds)
    f1_weighted = f1_score(y_test, preds, average="weighted")
    
    print(f"Test Samples: {len(X_test)}")
    print(f"Classification Accuracy: {acc * 100:.2f}%")
    print(f"Weighted F1-Score: {f1_weighted:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, preds, target_names=le.classes_))

def evaluate_model_b():
    print("\n=== EVALUATING MODEL B: LSTM RUL REGRESSOR ===")
    model_path = os.path.join(MODELS_DIR, "model_b_v1.pt")
    test_path = os.path.join(PROJECT_ROOT, "dataset", "CMaps", "test_FD001.txt")
    rul_path = os.path.join(PROJECT_ROOT, "dataset", "CMaps", "RUL_FD001.txt")
    scaler_path = os.path.join(MODELS_DIR, "scaler_MTR-05.pkl")
    
    if not (os.path.exists(model_path) and os.path.exists(test_path) and os.path.exists(rul_path) and os.path.exists(scaler_path)):
        print("Model B weights, scaler, or CMAPSS test files missing.")
        return
        
    scaler = joblib.load(scaler_path)
    
    # Load test raw data
    cols = ['engine_id', 'cycle', 'setting1', 'setting2', 'setting3'] + [f's{i}' for i in range(1, 22)]
    df = pd.read_csv(test_path, sep=r'\s+', header=None, names=cols)
    
    # Map CMAPSS fields to 25 feature columns (same logic as training)
    mapped_df = pd.DataFrame(index=df.index)
    mapped_df['temp_mean'] = df['s2']
    mapped_df['temp_max'] = df['s2'] + 2.0
    mapped_df['temp_min'] = df['s2'] - 2.0
    mapped_df['temp_slope'] = 0.05
    mapped_df['temp_std'] = 1.2
    
    mapped_df['vib_rms'] = df['s6']
    mapped_df['vib_peak'] = df['s6'] * 1.414
    mapped_df['vib_kurtosis'] = 3.0
    mapped_df['vib_skewness'] = 0.0
    mapped_df['vib_crest'] = 1.414
    mapped_df['vib_fft_low'] = df['s6'] * 50.0
    mapped_df['vib_fft_high'] = df['s6'] * 10.0
    
    mapped_df['current_mean'] = df['s12']
    mapped_df['current_std'] = 0.2
    mapped_df['current_thd'] = 0.02
    mapped_df['current_slope'] = 0.001
    
    mapped_df['rpm_mean'] = df['s11']
    mapped_df['rpm_std'] = 2.0
    mapped_df['rpm_drop_pct'] = np.clip((980.0 - df['s11']) / 980.0 * 100.0, 0, 100)
    
    mapped_df['torque_mean'] = df['s13']
    mapped_df['torque_std'] = 0.5
    mapped_df['torque_peak'] = df['s13'] + 1.0
    
    mapped_df['load_ratio'] = mapped_df['current_mean'] / (mapped_df['rpm_mean'] + 1e-8)
    mapped_df['temp_per_load'] = mapped_df['temp_mean'] / (mapped_df['current_mean'] + 1e-8)
    mapped_df['power_estimate'] = mapped_df['rpm_mean'] * mapped_df['torque_mean']
    
    df_features = mapped_df[FEATURE_COLS].copy()
    scaled_features = scaler.transform(df_features.values)
    
    # Load ground truth RUL
    y_true_rul = pd.read_csv(rul_path, header=None).values.flatten()
    y_true_rul = np.clip(y_true_rul, 0, 125)
    
    # Extract the last sequence of length 120 for each engine (unidirectional lookback)
    test_sequences = []
    valid_y_true = []
    
    for eng_idx, eng_id in enumerate(df['engine_id'].unique()):
        eng_mask = df['engine_id'] == eng_id
        eng_feats = scaled_features[eng_mask]
        
        # In CMAPSS, test sequences must be built with 120 timesteps
        if len(eng_feats) >= 120:
            seq = eng_feats[-120:]
            test_sequences.append(seq)
            valid_y_true.append(y_true_rul[eng_idx])
            
    if len(test_sequences) == 0:
        print("No engines have 120 cycles in test set.")
        return
        
    X_test = np.array(test_sequences, dtype=np.float32)
    y_test = np.array(valid_y_true, dtype=np.float32)
    
    # Init model
    model = RULPredictor(n_features=X_test.shape[2])
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
    
    with torch.no_grad():
        x_tensor = torch.tensor(X_test, dtype=torch.float32)
        preds = model(x_tensor).numpy()
        preds = np.clip(preds, 0, 125)
        
    # Compute metrics
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    
    # NASA score
    diff = preds - y_test
    nasa_score = np.sum(np.where(diff < 0, np.exp(-diff/13.0) - 1.0, np.exp(diff/10.0) - 1.0))
    
    print(f"Test Engines Evaluated: {len(X_test)}")
    print(f"Mean Absolute Error (MAE): {mae:.2f} cycles (Target: < 12)")
    print(f"Root Mean Squared Error (RMSE): {rmse:.2f} cycles")
    print(f"NASA Competition Score: {nasa_score:.2f}")

if __name__ == "__main__":
    evaluate_model_a1()
    evaluate_model_a2()
    evaluate_model_b()
