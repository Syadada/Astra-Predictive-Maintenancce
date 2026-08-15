# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd
# pyrefly: ignore [missing-import]
from scipy.signal import butter, filtfilt

class CleaningPipeline:
    # Physical boundaries - values outside these are physical impossibilities/sensor glitches
    PHYSICAL_LIMITS = {
        'temperature': (0.0, 200.0),    # °C
        'vibration_x': (-50.0, 50.0),   # g or mm/s
        'current_a'  : (0.0, 100.0),    # Ampere
        'rpm'        : (0.0, 4000.0),   # RPM
        'torque_nm'  : (-500.0, 500.0), # Nm
    }

    def clean(self, df: pd.DataFrame, motor=None) -> pd.DataFrame:
        """
        Cleans the input raw telemetry DataFrame for a specific motor:
        1. Drops duplicates by timestamp.
        2. Replaces out-of-bounds anomalies with None/NaN.
        3. Imputes missing values based on gap length.
        4. Synchronizes timestamps (rounds to the nearest second).
        5. Noise-filters vibration telemetry using a Butterworth low-pass filter.
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        # 1. Hapus duplikasi timestamp yang persis sama
        df = df.drop_duplicates(subset=['recorded_at'])
        
        # 2. Buang nilai di luar batas fisik -> jadikan None
        for col, (low, high) in self.PHYSICAL_LIMITS.items():
            if col in df.columns:
                # Convert to numeric if not already
                df[col] = pd.to_numeric(df[col], errors='coerce')
                mask = (df[col] < low) | (df[col] > high)
                df.loc[mask, col] = None

        # 3. Tangani missing value berdasarkan panjang gap
        for col in self.PHYSICAL_LIMITS.keys():
            if col in df.columns:
                null_count = df[col].isnull().sum()
                total = len(df)
                if total > 0:
                    null_pct = null_count / total
                    
                    if null_pct < 0.3:
                        # Gap pendek -> interpolasi linear
                        df[col] = df[col].interpolate(method='linear', limit=3)
                    elif null_pct < 0.7:
                        # Gap sedang -> forward fill dari nilai terakhir valid
                        df[col] = df[col].ffill(limit=5)
                    else:
                        # Gap panjang -> sensor kemungkinan mati, biarkan NULL
                        pass

        # 4. Sinkronisasi timestamp -> bulatkan ke detik terdekat
        df['recorded_at'] = pd.to_datetime(df['recorded_at']).dt.round('1s')
        
        # 5. Noise filtering untuk vibration -> Butterworth low-pass filter
        if 'vibration_x' in df.columns and len(df) > 15: # filtfilt requires enough points
            df['vibration_x'] = self._apply_lowpass_filter(df['vibration_x'])
            
        return df

    def _apply_lowpass_filter(self, series: pd.Series) -> pd.Series:
        # Check if we have enough non-null values to filter
        valid_indices = series.notna()
        if valid_indices.sum() > 15:
            try:
                # Butterworth low-pass filter: 4th-order, cutoff 10% of Nyquist frequency
                b, a = butter(4, 0.1, btype='low')
                
                # We filter on valid data points only, then map back
                valid_data = series[valid_indices].values
                filtered_data = filtfilt(b, a, valid_data)
                
                new_series = series.copy()
                new_series[valid_indices] = filtered_data
                return new_series
            except Exception as e:
                # Fallback to original in case of any filter error
                print(f"[CleaningPipeline] Butterworth filter warning: {e}")
                return series
        return series
