import os
import joblib
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "processed")

def check_model():
    model_path = os.path.join(MODEL_DIR, "cmapss_best_model.joblib")
    scaler_path = os.path.join(DATA_DIR, "cmapss_FD001_scaler.joblib")
    
    if not os.path.exists(model_path):
        print("Model file not found!")
        return
        
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    print("Model type:", type(model))
    if hasattr(model, "n_features_in_"):
        print("Expected input features:", model.n_features_in_)
        
    # Let's run a prediction like in predictor.py:
    # Cmapss base:
    base = scaler.data_min_ + 0.30 * scaler.data_range_
    window_raw = np.tile(base, (30, 1)).copy()
    
    # Predict for normal (deg = 0.0)
    window_scaled_0 = scaler.transform(window_raw)
    pred_0 = model.predict(window_scaled_0.reshape(1, -1))
    print("Prediction for deg = 0.0 (Normal):", pred_0)
    
    # Predict for degraded (deg = 1.0)
    deg = 1.0
    for step in range(30):
        t_frac = step / 29.0
        window_raw[step, 2] = scaler.data_min_[2] + (0.20 + 0.80 * deg * t_frac) * scaler.data_range_[2]
        window_raw[step, 7] = scaler.data_min_[7] + (0.20 + 0.80 * deg * t_frac) * scaler.data_range_[7]
        # Also modulate inlet temperature (idx 0) with UI temperature slider
        window_raw[step, 0] = scaler.data_min_[0] + (0.30 + 0.50 * (110 - 75) / 35.0) * scaler.data_range_[0]
        
    window_scaled_1 = scaler.transform(window_raw)
    pred_1 = model.predict(window_scaled_1.reshape(1, -1))
    print("Prediction for deg = 1.0 (Degraded):", pred_1)

if __name__ == "__main__":
    check_model()
