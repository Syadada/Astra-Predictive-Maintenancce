import os
import joblib
import numpy as np
import pandas as pd

# The exact list of features that will be used across our models
FEATURE_COLS = [
    'temp_mean', 'temp_max', 'temp_min', 'temp_slope', 'temp_std',
    'vib_rms', 'vib_peak', 'vib_kurtosis', 'vib_skewness', 'vib_crest',
    'vib_fft_low', 'vib_fft_high',
    'current_mean', 'current_std', 'current_thd', 'current_slope',
    'rpm_mean', 'rpm_std', 'rpm_drop_pct',
    'torque_mean', 'torque_std', 'torque_peak',
    'load_ratio', 'temp_per_load', 'power_estimate'
]

class SequenceBuilder:
    def __init__(self, scaler_dir='models'):
        self.scaler_dir = scaler_dir
        os.makedirs(scaler_dir, exist_ok=True)
        self.scalers = {}

    def get_scaler_path(self, motor_id):
        return os.path.join(self.scaler_dir, f'scaler_{motor_id}.pkl')

    def load_scaler(self, motor_id):
        if motor_id in self.scalers:
            return self.scalers[motor_id]
        
        path = self.get_scaler_path(motor_id)
        if os.path.exists(path):
            try:
                self.scalers[motor_id] = joblib.load(path)
                return self.scalers[motor_id]
            except Exception as e:
                print(f"[SequenceBuilder] Error loading scaler for {motor_id}: {e}")
        return None

    def save_scaler(self, motor_id, scaler):
        path = self.get_scaler_path(motor_id)
        joblib.dump(scaler, path)
        self.scalers[motor_id] = scaler
        print(f"[SequenceBuilder] Saved scaler to {path}")

    def build_sequence(self, windows_df: pd.DataFrame, motor_id: str, fit_scaler=False) -> np.ndarray:
        """
        Builds a scaled sequence array of shape (120, n_features) from a DataFrame of feature windows.
        If windows_df has fewer than 120 rows (but at least 20), it pads the beginning by repeating the first row.
        """
        if len(windows_df) < 20:
            raise ValueError(f"Not enough windows to build sequence. Got {len(windows_df)}, need at least 20.")

        # Ensure correct column ordering and select features
        df_feats = windows_df[FEATURE_COLS].copy()

        # Handle missing values: fill NaNs with 0.0 (or forward-fill first)
        df_feats = df_feats.ffill().bfill().fillna(0.0)

        # Convert to numpy array
        data_arr = df_feats.values

        # Apply scaling
        if fit_scaler:
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            data_arr = scaler.fit_transform(data_arr)
            self.save_scaler(motor_id, scaler)
        else:
            scaler = self.load_scaler(motor_id)
            if scaler is not None:
                try:
                    data_arr = scaler.transform(data_arr)
                except Exception as e:
                    print(f"[SequenceBuilder] Scaling failed for {motor_id}: {e}. Falling back to unscaled.")
            else:
                # If no scaler is found, log it and return unscaled (or fit a basic one to avoid crashing)
                print(f"[SequenceBuilder] WARNING: No scaler found for {motor_id}. Using raw features.")

        # Pad sequence if it is shorter than 120
        n_rows = data_arr.shape[0]
        if n_rows < 120:
            pad_len = 120 - n_rows
            first_row = data_arr[0:1, :]
            padding = np.repeat(first_row, pad_len, axis=0)
            sequence = np.vstack([padding, data_arr])
        else:
            # Take last 120 timesteps
            sequence = data_arr[-120:, :]

        return sequence
