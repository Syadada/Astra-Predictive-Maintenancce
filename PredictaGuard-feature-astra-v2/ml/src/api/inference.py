import os
import sys
import joblib
import torch
import numpy as np

# Add project path to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.models.model_a1 import LSTMAutoencoder
from src.models.model_b import RULPredictor
from src.pipeline.sequence import FEATURE_COLS

class InferenceOrchestrator:
    def __init__(self, models_dir='models'):
        self.models_dir = models_dir
        
        # Load Model A1 Anomaly Detection
        self.model_a1_path = os.path.join(models_dir, 'model_a1_v1.pt')
        self.meta_a1_path = os.path.join(models_dir, 'anomaly_meta.pkl')
        self.model_a1 = None
        self.threshold_a1 = None
        
        # Load Model A2 Classifier
        self.model_a2_path = os.path.join(models_dir, 'model_a2_v1.pkl')
        self.le_a2_path = os.path.join(models_dir, 'label_encoder_a2.pkl')
        self.model_a2 = None
        self.le_a2 = None
        
        # Load Model B RUL Predictor
        self.model_b_path = os.path.join(models_dir, 'model_b_v1.pt')
        self.model_b = None
        
        self.load_all_models()

    def load_all_models(self):
        # 1. Load LSTM Autoencoder
        if os.path.exists(self.model_a1_path) and os.path.exists(self.meta_a1_path):
            try:
                meta = joblib.load(self.meta_a1_path)
                self.threshold_a1 = meta['threshold']
                n_features = meta.get('n_features', len(FEATURE_COLS))
                
                self.model_a1 = LSTMAutoencoder(n_features=n_features)
                self.model_a1.load_state_dict(torch.load(self.model_a1_path, map_location=torch.device('cpu')))
                self.model_a1.eval()
                print("[Inference] Model A1 (LSTM Autoencoder) loaded successfully.")
            except Exception as e:
                print(f"[Inference] Error loading Model A1: {e}")
                
        # 2. Load Gradient Boosting Classifier
        if os.path.exists(self.model_a2_path) and os.path.exists(self.le_a2_path):
            try:
                self.model_a2 = joblib.load(self.model_a2_path)
                self.le_a2 = joblib.load(self.le_a2_path)
                print("[Inference] Model A2 (Fault Classifier) loaded successfully.")
            except Exception as e:
                print(f"[Inference] Error loading Model A2: {e}")
                
        # 3. Load RUL Predictor
        if os.path.exists(self.model_b_path):
            try:
                self.model_b = RULPredictor(n_features=len(FEATURE_COLS))
                self.model_b.load_state_dict(torch.load(self.model_b_path, map_location=torch.device('cpu')))
                self.model_b.eval()
                print("[Inference] Model B (RUL Predictor) loaded successfully.")
            except Exception as e:
                print(f"[Inference] Error loading Model B: {e}")

    def predict(self, sequence: np.ndarray, motor_id: str) -> dict:
        """
        Executes prediction using Model A1, Model A2, and Model B on a sequence array of shape (120, n_features).
        """
        # Ensure correct shape (1, 120, n_features)
        if len(sequence.shape) == 2:
            seq_tensor = torch.tensor(sequence, dtype=torch.float32).unsqueeze(0)
        else:
            seq_tensor = torch.tensor(sequence, dtype=torch.float32)
            
        results = {
            'anomaly_score': 0.0,
            'is_anomaly': False,
            'fault_type': 'healthy',
            'fault_confidence': 1.0,
            'rul_days': 125.0,
            'health_score': 100.0
        }

        # ─── Model A1: Anomaly Detection ───
        if self.model_a1 is not None and self.threshold_a1 is not None:
            try:
                errors = self.model_a1.reconstruction_error(seq_tensor)
                recon_err = float(errors[0].item())
                # Anomaly score is ratio of reconstruction error to threshold
                results['anomaly_score'] = recon_err / (self.threshold_a1 + 1e-8)
                results['is_anomaly'] = bool(recon_err > self.threshold_a1)
            except Exception as e:
                print(f"[Inference] Model A1 execution failed: {e}")
                
        # ─── Model A2: Fault Classification ───
        # Only classify if Model A1 flags an anomaly, otherwise it is 'healthy'
        if results['is_anomaly'] and self.model_a2 is not None and self.le_a2 is not None:
            try:
                # We classify using the features of the last timestep of the sequence (shape: 1, n_features)
                last_timestep = sequence[-1, :].reshape(1, -1)
                
                # Check for NaNs
                if np.isnan(last_timestep).any():
                    last_timestep = np.nan_to_num(last_timestep)
                    
                pred_class_idx = self.model_a2.predict(last_timestep)[0]
                probs = self.model_a2.predict_proba(last_timestep)[0]
                
                results['fault_type'] = str(self.le_a2.classes_[pred_class_idx])
                results['fault_confidence'] = float(probs[pred_class_idx])
            except Exception as e:
                print(f"[Inference] Model A2 execution failed: {e}")
        else:
            results['fault_type'] = 'healthy'
            results['fault_confidence'] = 1.0
            
        # ─── Model B: RUL Prediction ───
        if self.model_b is not None:
            try:
                with torch.no_grad():
                    rul_pred = self.model_b(seq_tensor).item()
                    
                # Clip RUL prediction between 0 and 125
                results['rul_days'] = float(np.clip(rul_pred, 0, 125))
                
                # Health score represents RUL as % (with 125 being 100%)
                results['health_score'] = float(np.clip((results['rul_days'] / 125.0) * 100.0, 0, 100))
            except Exception as e:
                print(f"[Inference] Model B execution failed: {e}")
                
        return results

if __name__ == '__main__':
    # Simple self-test
    orchestrator = InferenceOrchestrator()
    mock_seq = np.random.normal(0, 1, (120, len(FEATURE_COLS)))
    res = orchestrator.predict(mock_seq, 'MTR-01')
    print("Inference Test Output:", res)
