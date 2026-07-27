import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from scipy.fft import fft

class FeatureEngineeringPipeline:
    def engineer(self, df_clean: pd.DataFrame, motor) -> dict:
        """
        Processes a cleaned window of sensor data for a specific motor and
        returns a dictionary of engineered features.
        
        motor is an object/namedtuple/row with properties:
        - nominal_rpm
        - nominal_current
        - motor_id
        """
        features = {
            'motor_id': motor.motor_id,
            'window_start': df_clean['recorded_at'].min(),
            'window_end': df_clean['recorded_at'].max(),
            'created_at': pd.Timestamp.now()
        }

        # Initialize all features to None/NaN as safe default
        feature_keys = [
            'temp_mean', 'temp_max', 'temp_min', 'temp_slope', 'temp_std',
            'vib_rms', 'vib_peak', 'vib_kurtosis', 'vib_skewness', 'vib_crest',
            'vib_fft_low', 'vib_fft_high',
            'current_mean', 'current_std', 'current_thd', 'current_slope',
            'rpm_mean', 'rpm_std', 'rpm_drop_pct',
            'torque_mean', 'torque_std', 'torque_peak',
            'load_ratio', 'temp_per_load', 'power_estimate',
            'temp_null_pct', 'vib_null_pct', 'has_sensor_error'
        ]
        for key in feature_keys:
            if key not in features:
                features[key] = None

        # Calculate null percentages before dropping nulls
        features['temp_null_pct'] = float(df_clean['temperature'].isnull().mean()) if 'temperature' in df_clean.columns else 1.0
        features['vib_null_pct'] = float(df_clean['vibration_x'].isnull().mean()) if 'vibration_x' in df_clean.columns else 1.0
        
        # ── TEMPERATURE ──
        if 'temperature' in df_clean.columns:
            temp = df_clean['temperature'].dropna()
            if len(temp) > 0:
                features['temp_mean'] = float(temp.mean())
                features['temp_max'] = float(temp.max())
                features['temp_min'] = float(temp.min())
                features['temp_std'] = float(temp.std()) if len(temp) > 1 else 0.0
                if len(temp) > 1:
                    x = np.arange(len(temp))
                    features['temp_slope'] = float(np.polyfit(x, temp.values, 1)[0])
                else:
                    features['temp_slope'] = 0.0

        # ── VIBRATION ──
        if 'vibration_x' in df_clean.columns:
            vib = df_clean['vibration_x'].dropna()
            if len(vib) > 1:
                features['vib_rms'] = float(np.sqrt(np.mean(vib.values**2)))
                features['vib_peak'] = float(vib.abs().max())
                features['vib_kurtosis'] = float(kurtosis(vib.values))
                features['vib_skewness'] = float(skew(vib.values))
                features['vib_crest'] = float(vib.abs().max() / (np.sqrt(np.mean(vib.values**2)) + 1e-8))

                # FFT Energy bands
                try:
                    fft_vals = np.abs(fft(vib.values))
                    n = len(fft_vals)
                    # Low frequency: first 25% of FFT bins (fault range)
                    # High frequency: next 25% of FFT bins
                    features['vib_fft_low'] = float(np.sum(fft_vals[:n//4]**2))
                    features['vib_fft_high'] = float(np.sum(fft_vals[n//4:n//2]**2))
                except Exception as e:
                    print(f"[FeatureEngineeringPipeline] FFT error: {e}")
                    features['vib_fft_low'] = 0.0
                    features['vib_fft_high'] = 0.0

        # ── CURRENT ──
        if 'current_a' in df_clean.columns:
            curr = df_clean['current_a'].dropna()
            if len(curr) > 0:
                features['current_mean'] = float(curr.mean())
                features['current_std'] = float(curr.std()) if len(curr) > 1 else 0.0
                # Proxy for THD: current standard deviation / current mean
                features['current_thd'] = float(curr.std() / (curr.mean() + 1e-8)) if len(curr) > 1 else 0.0
                if len(curr) > 1:
                    features['current_slope'] = float(np.polyfit(np.arange(len(curr)), curr.values, 1)[0])
                else:
                    features['current_slope'] = 0.0

        # ── RPM ──
        if 'rpm' in df_clean.columns:
            rpm = df_clean['rpm'].dropna()
            if len(rpm) > 0:
                features['rpm_mean'] = float(rpm.mean())
                features['rpm_std'] = float(rpm.std()) if len(rpm) > 1 else 0.0
                # % drop from nominal RPM
                nominal = getattr(motor, 'nominal_rpm', 1500.0)
                if nominal > 0:
                    features['rpm_drop_pct'] = float(max(0.0, (nominal - rpm.mean()) / nominal * 100.0))
                else:
                    features['rpm_drop_pct'] = 0.0

        # ── TORQUE ──
        if 'torque_nm' in df_clean.columns:
            torq = df_clean['torque_nm'].dropna()
            if len(torq) > 0:
                features['torque_mean'] = float(torq.mean())
                features['torque_std'] = float(torq.std()) if len(torq) > 1 else 0.0
                features['torque_peak'] = float(torq.abs().max())

        # ── CROSS-PARAMETER FEATURES ──
        if features['current_mean'] is not None and features['rpm_mean'] is not None:
            features['load_ratio'] = float(features['current_mean'] / (features['rpm_mean'] + 1e-8))

        if features['temp_mean'] is not None and features['current_mean'] is not None:
            features['temp_per_load'] = float(features['temp_mean'] / (features['current_mean'] + 1e-8))

        if features['rpm_mean'] is not None and features['torque_mean'] is not None:
            # Power estimate ∝ RPM * Torque
            features['power_estimate'] = float(features['rpm_mean'] * features['torque_mean'])

        # ── DATA QUALITY FLAGS ──
        # Check if more than 50% of any column row is null/missing
        null_counts_per_row = df_clean.isnull().any(axis=1).sum()
        features['has_sensor_error'] = bool(null_counts_per_row > len(df_clean) * 0.5)

        return features
