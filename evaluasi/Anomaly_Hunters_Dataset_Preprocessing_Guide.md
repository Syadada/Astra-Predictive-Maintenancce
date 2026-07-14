# DATASET & PREPROCESSING BEST PRACTICES
## Anomaly Hunters - Technical Implementation Guide

---

## **CURRENT STATUS ANALYSIS**

Dari proposal kalian, kami tau kalian sudah:
- ✓ Dataset prepared (EDA done)
- ✓ Preprocessing done (normalization, feature engineering)
- ✓ Synthetic data generated (Monte Carlo)

**Masalah yang kalian face:** "Front-end kurang relevan dengan data"

Ini biasanya terjadi karena:
1. **Data format mismatch** - Backend output tidak match frontend expected format
2. **Missing intermediate processing** - Raw ML output tidak langsung displayable
3. **Lack of context** - Model output hanya angka, tanpa explanation untuk UI

Mari kita fix ini step-by-step.

---

## **PART A: DATASET STRUCTURE YANG OPTIMAL**

### **Target Dataset Format (Recommended)**

Berdasarkan proposal kalian, dataset HARUS punya struktur ini:

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# IDEAL DATASET STRUCTURE
dataset = {
    'metadata': {
        'equipment_type': 'PUMP',        # PUMP, MIXER, SPRAY, COMPRESSOR
        'equipment_id': 'PUMP-01',
        'installation_date': '2023-01-15',
        'specifications': {
            'nominal_voltage': 380,       # Volt
            'nominal_current': 12,        # Ampere
            'max_vibration': 15,          # mm/s
            'max_temperature': 90,        # Celsius
        }
    },
    
    'sensor_data': {
        # REAL-TIME STREAMS (HIGH FREQUENCY)
        'timestamp': pd.DatetimeIndex([...]),  # Every 5 seconds
        'vibration_mms': [...],                # mm/s - accelerometer
        'temperature_c': [...],                # °C - PT100 RTD
        'current_a': [...],                    # Ampere - CT sensor
        'pressure_bar': [...],                 # bar - pressure transducer
    },
    
    'maintenance_events': {
        # DISCRETE EVENTS (MAINTENANCE LOG)
        'event_timestamp': pd.DatetimeIndex([...]),
        'event_type': ['bearing_replacement', 'oil_change', ...],
        'description': ['Bearing assembly replaced', ...],
        'mtbf_hours_before': [720, 600, ...],  # Hours to failure
        'mttr_hours': [4, 3, ...],             # Hours to repair
    },
    
    'operational_context': {
        # CONTEXTUAL DATA (PRODUCTION LOAD, ETC)
        'timestamp': pd.DatetimeIndex([...]),
        'production_load_percent': [...],      # 0-100%
        'ambient_temperature_c': [...],        # Room temp
        'production_line_status': ['running', 'idle', ...],
    }
}
```

### **CSV Format (Practical)**

```csv
timestamp,equipment_id,vibration_mms,temperature_c,current_a,pressure_bar,production_load_percent,ambient_temp_c,maintenance_event,mtbf_before_failure_hours,mttr_hours
2024-01-15 10:00:00,PUMP-01,9.2,67.3,12.1,3.5,85,25,None,720,0
2024-01-15 10:05:00,PUMP-01,9.4,67.8,12.0,3.5,85,25,None,719.92,0
2024-01-15 10:10:00,PUMP-01,10.1,68.2,12.2,3.6,85,25,None,719.83,0
...
2024-02-10 14:00:00,PUMP-01,14.5,82.1,13.8,4.2,90,26,bearing_replacement,0,4
2024-02-10 18:00:00,PUMP-01,9.1,68.0,12.1,3.5,85,25,None,720,0
```

### **Data Quality Checks (BEFORE using)**

```python
class DataQualityValidator:
    def __init__(self, df):
        self.df = df
        self.issues = []
    
    def check_missing_values(self):
        """Identify missing sensor readings"""
        for col in ['vibration_mms', 'temperature_c', 'current_a']:
            missing_pct = self.df[col].isnull().sum() / len(self.df) * 100
            if missing_pct > 5:  # Flag if >5% missing
                self.issues.append(f"{col}: {missing_pct:.1f}% missing")
        
        return self.df.isnull().sum()
    
    def check_outliers(self):
        """Detect sensor outliers (stuck values, jumps)"""
        for col in ['vibration_mms', 'temperature_c', 'current_a']:
            # IQR method
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR  # 3-sigma rule
            upper_bound = Q3 + 3 * IQR
            
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)]
            if len(outliers) > 0:
                self.issues.append(f"{col}: {len(outliers)} outliers detected")
        
        return outliers
    
    def check_timestamps(self):
        """Verify timestamp continuity (no gaps)"""
        time_diff = self.df['timestamp'].diff()
        expected_interval = pd.Timedelta(seconds=5)  # 5-second samples
        
        gaps = time_diff[time_diff != expected_interval]
        if len(gaps) > 0:
            self.issues.append(f"Timestamp gaps: {len(gaps)} irregular intervals")
        
        return gaps
    
    def check_sensor_ranges(self):
        """Verify sensors within physical limits"""
        limits = {
            'vibration_mms': (0, 20),
            'temperature_c': (0, 120),
            'current_a': (0, 30),
            'pressure_bar': (0, 10)
        }
        
        for col, (min_val, max_val) in limits.items():
            out_of_range = self.df[(self.df[col] < min_val) | (self.df[col] > max_val)]
            if len(out_of_range) > 0:
                self.issues.append(f"{col}: {len(out_of_range)} values out of range [{min_val}-{max_val}]")
        
        return self.issues
    
    def report(self):
        """Generate data quality report"""
        print("=" * 50)
        print("DATA QUALITY VALIDATION REPORT")
        print("=" * 50)
        
        self.check_missing_values()
        self.check_outliers()
        self.check_timestamps()
        self.check_sensor_ranges()
        
        if self.issues:
            print(f"\n⚠️  {len(self.issues)} issues found:")
            for issue in self.issues:
                print(f"  - {issue}")
        else:
            print("\n✓ All checks passed!")

# Usage
validator = DataQualityValidator(df)
validator.report()
```

---

## **PART B: PREPROCESSING PIPELINE (PROPER IMPLEMENTATION)**

### **Step 1: Data Loading & Initial Cleaning**

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
import warnings
warnings.filterwarnings('ignore')

class PreprocessingPipeline:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)
        self.scalers = {}  # Store scalers untuk inverse transform later
        
    def load_and_validate(self):
        """Load data dan perform initial validation"""
        # Parse timestamp
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        # Sort by timestamp
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        
        # Handle missing values (forward-fill untuk sensor data)
        sensor_cols = ['vibration_mms', 'temperature_c', 'current_a', 'pressure_bar']
        for col in sensor_cols:
            self.df[col] = self.df[col].fillna(method='ffill').fillna(method='bfill')
        
        return self.df
    
    def create_failure_labels(self):
        """Create binary label: will failure occur in next 72 hours?"""
        self.df['failure_in_72h'] = 0
        
        # Find all maintenance events
        maintenance_idx = self.df[self.df['maintenance_event'].notna()].index
        
        for idx in maintenance_idx:
            maintenance_time = self.df.loc[idx, 'timestamp']
            
            # Label all rows in previous 72 hours as "pre-failure"
            window_start = idx - (72 * 60 * 60 / 5)  # Assume 5-second samples
            if window_start < 0:
                window_start = 0
            
            self.df.loc[int(window_start):idx, 'failure_in_72h'] = 1
        
        return self.df
    
    def create_rul_labels(self):
        """Create RUL (Remaining Useful Life) labels in hours"""
        self.df['rul_hours'] = np.inf  # Default: no failure
        
        # For each row, find nearest maintenance event
        maintenance_events = self.df[self.df['maintenance_event'].notna()]['timestamp'].values
        
        for idx, row in self.df.iterrows():
            time = row['timestamp']
            
            # Find next maintenance event
            future_events = maintenance_events[maintenance_events > time]
            
            if len(future_events) > 0:
                next_event = future_events[0]
                hours_to_failure = (next_event - time) / np.timedelta64(1, 'h')
                self.df.loc[idx, 'rul_hours'] = hours_to_failure
            else:
                # No future failure recorded
                self.df.loc[idx, 'rul_hours'] = 999
        
        return self.df
    
    def remove_outliers(self, threshold=3):
        """Remove statistical outliers using z-score"""
        sensor_cols = ['vibration_mms', 'temperature_c', 'current_a', 'pressure_bar']
        
        for col in sensor_cols:
            mean = self.df[col].mean()
            std = self.df[col].std()
            
            # Z-score
            z_scores = np.abs((self.df[col] - mean) / std)
            
            # Keep only rows with z-score < threshold
            self.df = self.df[z_scores < threshold]
        
        self.df = self.df.reset_index(drop=True)
        return self.df
    
    def normalize_sensors(self, method='standard'):
        """Normalize sensor data to zero-mean, unit-variance (or 0-1)"""
        sensor_cols = ['vibration_mms', 'temperature_c', 'current_a', 'pressure_bar']
        
        if method == 'standard':  # Z-score normalization
            scaler = StandardScaler()
        elif method == 'minmax':  # 0-1 normalization
            scaler = MinMaxScaler()
        
        self.df[sensor_cols] = scaler.fit_transform(self.df[sensor_cols])
        self.scalers['sensor_scaler'] = scaler  # Save for inverse transform
        
        return self.df
    
    def create_features(self):
        """Create derived features untuk ML models"""
        # Rolling statistics (3-hour window)
        window_size = int(3 * 3600 / 5)  # 3 hours in 5-second samples
        
        for col in ['vibration_mms', 'temperature_c', 'current_a']:
            # Mean
            self.df[f'{col}_rolling_mean'] = self.df[col].rolling(window=window_size, min_periods=1).mean()
            
            # Std deviation
            self.df[f'{col}_rolling_std'] = self.df[col].rolling(window=window_size, min_periods=1).std()
            
            # Min/Max
            self.df[f'{col}_rolling_min'] = self.df[col].rolling(window=window_size, min_periods=1).min()
            self.df[f'{col}_rolling_max'] = self.df[col].rolling(window=window_size, min_periods=1).max()
        
        # Rate of change (derivative)
        for col in ['vibration_mms', 'temperature_c', 'current_a']:
            self.df[f'{col}_diff'] = self.df[col].diff()
            self.df[f'{col}_diff'] = self.df[f'{col}_diff'].fillna(0)
        
        return self.df
    
    def prepare_sequences(self, window_size=60):
        """
        Convert time-series into sequences untuk LSTM
        Input: (N_samples, window_size, n_features)
        Output: Suitable untuk LSTM Autoencoder
        """
        sensor_cols = ['vibration_mms', 'temperature_c', 'current_a', 'pressure_bar']
        
        X_sequences = []
        y_labels_anomaly = []
        y_labels_rul = []
        
        for i in range(len(self.df) - window_size):
            # Get window
            window = self.df.iloc[i:i+window_size][sensor_cols].values
            X_sequences.append(window)
            
            # Label: future failure (next timestep after window)
            y_labels_anomaly.append(self.df.iloc[i+window_size]['failure_in_72h'])
            y_labels_rul.append(self.df.iloc[i+window_size]['rul_hours'])
        
        X_sequences = np.array(X_sequences)  # (N, 60, 4)
        y_anomaly = np.array(y_labels_anomaly)
        y_rul = np.array(y_labels_rul)
        
        return X_sequences, y_anomaly, y_rul
    
    def run_full_pipeline(self):
        """Execute semua preprocessing steps"""
        print("Loading data...")
        self.load_and_validate()
        
        print("Creating labels...")
        self.create_failure_labels()
        self.create_rul_labels()
        
        print("Removing outliers...")
        self.remove_outliers(threshold=3)
        
        print("Normalizing sensors...")
        self.normalize_sensors(method='standard')
        
        print("Creating features...")
        self.create_features()
        
        print("Preparing sequences...")
        X_seq, y_anom, y_rul = self.prepare_sequences(window_size=60)
        
        print(f"\n✓ Preprocessing complete!")
        print(f"  Input shape: {X_seq.shape}  (sequences, window, features)")
        print(f"  Anomaly labels: {y_anom.shape}")
        print(f"  RUL labels: {y_rul.shape}")
        
        return {
            'X': X_seq,
            'y_anomaly': y_anom,
            'y_rul': y_rul,
            'df_processed': self.df,
            'scalers': self.scalers
        }

# Usage
pipeline = PreprocessingPipeline('kerry_sensor_data.csv')
processed_data = pipeline.run_full_pipeline()

X = processed_data['X']
y_anomaly = processed_data['y_anomaly']
y_rul = processed_data['y_rul']
```

---

## **PART C: SYNTHETIC DATA GENERATION (Detailed)**

### **Why Synthetic Data?**

```
Real problem:
- Historical failures sparse (maybe 5-10 examples per equipment type)
- Machine learning needs 100s of examples untuk generalize
- Transfer learning dari public datasets helps, tapi domain-specific
  synthetic data LEBIH realistic

Solution: Generate synthetic degradation curves yang mimic real failure patterns
```

### **Implementation**

```python
import numpy as np
from scipy.interpolate import interp1d
from sklearn.preprocessing import StandardScaler

class SyntheticDataGenerator:
    """
    Generate realistic synthetic sensor data yang menunjukkan
    equipment degradation dari healthy → failure
    """
    
    def __init__(self, equipment_specs):
        """
        equipment_specs: Dictionary dengan specifications per equipment type
        
        Example:
        {
            'PUMP': {
                'healthy_vibration_mean': 9,
                'healthy_vibration_std': 1,
                'failure_vibration': 15,
                'degradation_rate_mean': 0.02,  # mm/s per hour
                'ttf_mean': 720,  # hours to failure
                'ttf_std': 100,
            },
            ...
        }
        """
        self.specs = equipment_specs
    
    def generate_degradation_curve(self, equipment_type, num_failures=100):
        """
        Generate realistic failure time distribution
        
        Uses: Weibull distribution (common untuk reliability engineering)
        """
        ttf = np.random.gamma(
            shape=5,  # Shape parameter (affects curve curvature)
            scale=self.specs[equipment_type]['ttf_mean'] / 5,  # Scale
            size=num_failures
        )
        
        # Ensure minimum TTF > 0
        ttf = np.maximum(ttf, 10)
        
        return ttf
    
    def generate_sensor_trajectory(self, ttf_hours, equipment_type):
        """
        Generate realistic sensor time-series untuk given failure time
        
        Models: S-curve degradation (slow start → rapid → failure)
        """
        # Number of samples (5-second intervals)
        num_samples = int(ttf_hours * 3600 / 5)
        time_array = np.arange(num_samples) / (3600/5)  # in hours
        
        # Normalized time (0 to 1)
        t_norm = time_array / ttf_hours
        
        # S-curve degradation function (sigmoid-like)
        # Slow start, accelerating, then rapid failure
        degradation = 1 / (1 + np.exp(-10 * (t_norm - 0.5)))  # Values 0->1
        
        # Scale to sensor ranges
        specs = self.specs[equipment_type]
        
        # Vibration: healthy_mean + degradation * (failure_level - healthy_mean)
        vibration = (specs['healthy_vibration_mean'] + 
                    degradation * (specs['failure_vibration'] - specs['healthy_vibration_mean']))
        
        # Temperature: typically increases with failure
        temperature = (specs['healthy_temp_mean'] + 
                      degradation * (specs['failure_temp'] - specs['healthy_temp_mean']))
        
        # Current: may increase slightly due to friction
        current = (specs['nominal_current'] + 
                  degradation * specs['failure_current_increase'])
        
        # Add realistic noise
        vibration += np.random.normal(0, specs['healthy_vibration_std'], num_samples)
        temperature += np.random.normal(0, 1.5, num_samples)
        current += np.random.normal(0, 0.3, num_samples)
        
        # Clip to physical limits
        vibration = np.clip(vibration, 0, specs['max_vibration'])
        temperature = np.clip(temperature, 0, specs['max_temperature'])
        current = np.clip(current, 0, specs['max_current'])
        
        return {
            'vibration': vibration,
            'temperature': temperature,
            'current': current,
            'time_hours': time_array,
            'ttf_hours': ttf_hours
        }
    
    def generate_synthetic_dataset(self, equipment_type, n_synthetic_failures=100):
        """
        Generate complete synthetic dataset untuk training
        """
        synthetic_data = []
        
        for i in range(n_synthetic_failures):
            # Generate random TTF
            ttf = self.generate_degradation_curve(equipment_type, num_failures=1)[0]
            
            # Generate sensor trajectory
            trajectory = self.generate_sensor_trajectory(ttf, equipment_type)
            
            # Create DataFrame row untuk each sample
            for sample_idx in range(len(trajectory['vibration'])):
                synthetic_data.append({
                    'equipment_id': f"{equipment_type}-SYN-{i:03d}",
                    'synthetic_failure_id': i,
                    'time_to_failure_hours': trajectory['ttf_hours'],
                    'time_in_failure_cycle_hours': trajectory['time_hours'][sample_idx],
                    'vibration_mms': trajectory['vibration'][sample_idx],
                    'temperature_c': trajectory['temperature'][sample_idx],
                    'current_a': trajectory['current'][sample_idx],
                    'failure_in_72h': 1 if trajectory['time_hours'][sample_idx] > (trajectory['ttf_hours'] - 72) else 0,
                })
        
        return pd.DataFrame(synthetic_data)
    
    def mix_real_and_synthetic(self, df_real, equipment_type, synthetic_ratio=0.5):
        """
        Mix real data dengan synthetic untuk balanced training set
        
        synthetic_ratio: 0.5 = 50% synthetic, 50% real
        """
        df_synthetic = self.generate_synthetic_dataset(equipment_type, n_synthetic_failures=50)
        
        # Adjust columns to match
        df_real['synthetic_failure_id'] = -1  # Mark as real
        
        # Concatenate
        df_mixed = pd.concat([df_real, df_synthetic], ignore_index=True)
        
        # Shuffle
        df_mixed = df_mixed.sample(frac=1).reset_index(drop=True)
        
        return df_mixed

# Usage
specs = {
    'PUMP': {
        'healthy_vibration_mean': 9,
        'healthy_vibration_std': 1.2,
        'failure_vibration': 15,
        'healthy_temp_mean': 68,
        'failure_temp': 88,
        'nominal_current': 12,
        'failure_current_increase': 3,
        'max_vibration': 20,
        'max_temperature': 100,
        'max_current': 30,
        'ttf_mean': 720,
        'ttf_std': 100,
    },
    # Add other equipment types...
}

generator = SyntheticDataGenerator(specs)

# Mix real + synthetic untuk balanced training
df_real = pd.read_csv('kerry_real_data.csv')
df_mixed = generator.mix_real_and_synthetic(df_real, 'PUMP', synthetic_ratio=0.6)

print(f"Original dataset: {len(df_real)} rows")
print(f"After synthetic augmentation: {len(df_mixed)} rows")
print(f"Synthetic fraction: {(len(df_mixed) - len(df_real)) / len(df_mixed) * 100:.1f}%")
```

---

## **PART D: TRAIN-TEST SPLIT (Time-Series aware)**

```python
from sklearn.model_selection import TimeSeriesSplit

def split_timeseries_data(X, y, test_size=0.2, n_splits=5):
    """
    Proper time-series split (NO data leakage!)
    
    ❌ WRONG (Random split): Train 2024-01 mix dengan 2024-03
                            Bisa cause future-leakage
    
    ✓ RIGHT (Time split):   Train: 2024-01 to 2024-02
                            Test: 2024-03 onwards
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    # Get last split for final train-test
    splits = list(tscv.split(X))
    train_idx, test_idx = splits[-1]
    
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    
    print(f"Train set: {len(X_train)} sequences ({len(X_train)/len(X)*100:.1f}%)")
    print(f"Test set: {len(X_test)} sequences ({len(X_test)/len(X)*100:.1f}%)")
    print(f"Train period: Earliest {len(X_train)} samples")
    print(f"Test period: Latest {len(X_test)} samples (no leakage!)")
    
    return X_train, X_test, y_train, y_test

# Usage
X_train, X_test, y_train, y_test = split_timeseries_data(X, y_anomaly)

# Double-check no leakage
assert max(np.where(y_train == 1)[0]) < min(np.where(y_test == 1)[0]), "Data leakage detected!"
```

---

## **PART E: CHECKLIST PREPROCESSING KALIAN**

```
[✓] Dataset loaded dan validated
[?] Missing values handled correctly?
[?] Outliers removed (z-score or IQR)?
[?] Sensors normalized (z-score or minmax)?
[?] Failure labels created (binary: failure in 72h)?
[?] RUL labels created (continuous: hours to failure)?
[?] Feature engineering done (rolling stats, derivatives)?
[?] Sequences created for LSTM (shape: N x 60 x 4)?
[?] Synthetic data mixed dengan real data (ratio checked)?
[?] Train-test split time-aware (NO data leakage)?

RECOMMENDATION:
If ada yang [?], fix sekarang sebelum training model.
Foundation yang lemah → model yang tidak reliable → presentation fail.
```

---

## **SUMMARY: PREPROCESSING CHECKLIST FOR TOMORROW**

```
✓ Dataset structure adalah CSV dengan sensor + maintenance + RUL
✓ Preprocessing pipeline include: validation, cleaning, normalization, feature engineering
✓ Synthetic data realistic dan coherent dengan real data  
✓ Time-series split (tidak ada leakage)
✓ All preprocessing scripts documented dan reproducible

KALAU PUNYA ISSUE:
1. Data mismatch (format) → Fix Dataset structure section
2. Frontend dashboard kosong → Fix Data pipeline output format
3. Model performance rendah → Check preprocessing quality (garbage in = garbage out)
```

