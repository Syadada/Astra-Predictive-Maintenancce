import os
# Force OpenMP to use 1 thread to avoid deadlocks on Windows
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

print("Starting script...")
import joblib
print("Imported joblib")
import numpy as np
print("Imported numpy")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "processed")

_CWRU_NORMAL_MEANS = [0.2051, -0.2065, 0.0125, 0.0650, 0.0663, -0.1731, -0.0956, 3.094,   5.529]
_CWRU_FAULT_MEANS  = [4.8273, -4.8405, 0.0121, 1.0566, 1.0564,  0.0716,  3.8953, 4.5911, 92.053]

def test():
    print("Loading model...")
    model_path = os.path.join(MODEL_DIR, "cwru_best_model.joblib")
    print(f"Model path: {model_path}")
    model = joblib.load(model_path)
    print("Model loaded successfully!")
    
    print("Loading label encoder...")
    le_path = os.path.join(DATA_DIR, "cwru_label_encoder.joblib")
    le = joblib.load(le_path)
    print("Label encoder loaded successfully!")
    
    # We will test predictions for severity from 0.0 to 1.0
    for severity in [0.0, 0.5, 1.0]:
        normal_ratio = max(0.0, 1.0 - severity)
        fault_ratio  = 1.0 - normal_ratio
        
        features_raw = np.zeros(9)
        for idx in range(9):
            features_raw[idx] = normal_ratio * _CWRU_NORMAL_MEANS[idx] + fault_ratio * _CWRU_FAULT_MEANS[idx]
            
        mean_ep = (np.array(_CWRU_NORMAL_MEANS) + np.array(_CWRU_FAULT_MEANS)) / 2.0
        std_ep = np.abs(np.array(_CWRU_FAULT_MEANS) - np.array(_CWRU_NORMAL_MEANS)) / 2.0
        std_ep = np.where(std_ep == 0, 1.0, std_ep)
        
        features_scaled_ep = (features_raw - mean_ep) / std_ep
        print(f"Predicting for severity {severity:.1f}...")
        pred_idx_ep = model.predict(features_scaled_ep.reshape(1, -1))[0]
        probs_ep = model.predict_proba(features_scaled_ep.reshape(1, -1))[0]
        print(f"Severity {severity:.1f}: Class: {le.classes_[pred_idx_ep]} (confidence: {probs_ep[pred_idx_ep]:.4f})")

if __name__ == "__main__":
    test()
