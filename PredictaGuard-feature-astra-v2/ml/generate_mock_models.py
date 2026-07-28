import os
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier, MLPRegressor

# Paths
ml_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.join(ml_dir, "models")
proc_dir = os.path.join(ml_dir, "data", "processed")
syn_dir = os.path.join(ml_dir, "data", "synthetic")
os.makedirs(model_dir, exist_ok=True)
os.makedirs(proc_dir, exist_ok=True)
os.makedirs(syn_dir, exist_ok=True)

print("Generating mock scalers and encoders...")

# 1. skab_scaler.joblib (8 sensors)
scaler_skab = StandardScaler()
X_skab_dummy = np.random.randn(100, 8)
scaler_skab.fit(X_skab_dummy)
joblib.dump(scaler_skab, os.path.join(proc_dir, "skab_scaler.joblib"))

# 2. cwru_scaler.joblib (9 features)
scaler_cwru = StandardScaler()
X_cwru_dummy = np.random.randn(100, 9)
scaler_cwru.fit(X_cwru_dummy)
joblib.dump(scaler_cwru, os.path.join(proc_dir, "cwru_scaler.joblib"))

# 3. cmapss_FD001_scaler.joblib (14 sensors)
scaler_cmapss = MinMaxScaler()
X_cmapss_dummy = np.random.rand(100, 14)
scaler_cmapss.fit(X_cmapss_dummy)
joblib.dump(scaler_cmapss, os.path.join(proc_dir, "cmapss_FD001_scaler.joblib"))

# 4. cwru_label_encoder.joblib
classes = [
    "Normal_1", "Ball_007_1", "OR_014_6_1", "Ball_014_1", "Ball_021_1",
    "IR_007_1", "IR_014_1", "IR_021_1", "OR_007_6_1", "OR_021_6_1"
]
le = LabelEncoder()
le.fit(classes)
joblib.dump(le, os.path.join(proc_dir, "cwru_label_encoder.joblib"))

# 5. cwru_features.npz
X_train_cwru = np.random.randn(200, 9)
np.savez_compressed(os.path.join(proc_dir, "cwru_features.npz"), X_train=X_train_cwru)

# 6. skab_windows.npz (X_test: (234, 60, 8), y_test: (234,))
print("Generating mock skab_windows.npz...")
X_skab_test = np.random.randn(234, 60, 8).astype(np.float32)
y_skab_test = np.random.choice([0, 1], size=234).astype(np.int32)
np.savez_compressed(
    os.path.join(proc_dir, "skab_windows.npz"),
    X_train=np.random.randn(10, 60, 8).astype(np.float32),
    y_train=np.random.choice([0, 1], size=10).astype(np.int32),
    X_val=np.random.randn(10, 60, 8).astype(np.float32),
    y_val=np.random.choice([0, 1], size=10).astype(np.int32),
    X_test=X_skab_test,
    y_test=y_skab_test
)

# 7. cmapss_FD001.npz (X_test: (1000, 30, 14), y_test: (1000,))
print("Generating mock cmapss_FD001.npz...")
X_cmapss_test = np.random.rand(1000, 30, 14).astype(np.float32)
y_cmapss_test = np.random.uniform(0, 125, size=1000).astype(np.float32)
np.savez_compressed(
    os.path.join(proc_dir, "cmapss_FD001.npz"),
    X_train=np.random.rand(10, 30, 14).astype(np.float32),
    y_train=np.random.uniform(0, 125, size=10).astype(np.float32),
    X_val=np.random.rand(10, 30, 14).astype(np.float32),
    y_val=np.random.uniform(0, 125, size=10).astype(np.float32),
    X_test=X_cmapss_test,
    y_test=y_cmapss_test
)

print("Training mock ML models...")

# 8. skab_best_model.joblib (flattened window: 60 * 8 = 480 features)
X_skab_flat = np.random.randn(100, 480)
y_skab = np.random.choice([0, 1], size=100)
skab_model = RandomForestClassifier(n_estimators=10, random_state=42)
skab_model.fit(X_skab_flat, y_skab)
joblib.dump(skab_model, os.path.join(model_dir, "skab_best_model.joblib"))

# 9. cwru_best_model.joblib & cwru_random_forest.joblib (9 features, 10 classes)
X_cwru = np.random.randn(100, 9)
y_cwru = np.random.choice(classes, size=100)
# Convert y_cwru to encoded values
y_cwru_enc = le.transform(y_cwru)

# cwru_best_model
cwru_model = MLPClassifier(hidden_layer_sizes=(10,), max_iter=20, random_state=42)
cwru_model.fit(X_cwru, y_cwru_enc)
joblib.dump(cwru_model, os.path.join(model_dir, "cwru_best_model.joblib"))

# cwru_random_forest
cwru_rf = RandomForestClassifier(n_estimators=10, random_state=42)
cwru_rf.fit(X_cwru, y_cwru_enc)
joblib.dump(cwru_rf, os.path.join(model_dir, "cwru_random_forest.joblib"))

# 10. cmapss_best_model.joblib (flattened window: 30 * 14 = 420 features)
X_cmapss_flat = np.random.randn(100, 420)
y_cmapss = np.random.uniform(0, 125, size=100)
cmapss_model = MLPRegressor(hidden_layer_sizes=(10,), max_iter=20, random_state=42)
cmapss_model.fit(X_cmapss_flat, y_cmapss)
joblib.dump(cmapss_model, os.path.join(model_dir, "cmapss_best_model.joblib"))

print("Generating mock synthetic CSVs...")

# Generate timestamps
timestamps = pd.date_range("2025-07-01 06:00:00", periods=1000, freq="1min")

# Pump CSV
pump_df = pd.DataFrame({
    "timestamp": timestamps,
    "flow_rate_lpm": np.random.uniform(150, 250, size=1000),
    "inlet_pressure_bar": np.random.uniform(1.5, 2.5, size=1000),
    "outlet_pressure_bar": np.random.uniform(3.0, 4.0, size=1000),
    "motor_current_A": np.random.uniform(1.0, 3.0, size=1000),
    "vibration_rms_mm_s": np.random.uniform(0.5, 9.5, size=1000),
    "temperature_C": np.random.uniform(20, 80, size=1000),
    "motor_voltage_V": np.random.uniform(220, 240, size=1000),
    "health_state": np.random.choice(["normal", "degrading", "fault"], size=1000),
    "rul_hours": np.random.uniform(0, 720, size=1000),
    "fault_type": np.random.choice(["normal", "cavitation", "bearing_wear", "overload", "seal_leak"], size=1000),
    "is_running": np.ones(1000, dtype=int),
})
pump_df.to_csv(os.path.join(syn_dir, "pump_data.csv"), index=False)

# Mixer CSV
mixer_df = pd.DataFrame({
    "timestamp": timestamps,
    "mixer_speed_rpm": np.random.uniform(100, 200, size=1000),
    "motor_current_A": np.random.uniform(1.0, 3.0, size=1000),
    "vibration_rms_x_mm_s": np.random.uniform(0.5, 8.5, size=1000),
    "vibration_rms_y_mm_s": np.random.uniform(0.5, 8.5, size=1000),
    "gearbox_temperature_C": np.random.uniform(20, 80, size=1000),
    "process_viscosity_cP": np.random.uniform(5, 50, size=1000),
    "power_kW": np.random.uniform(0.5, 2.0, size=1000),
    "health_state": np.random.choice(["normal", "degrading", "fault"], size=1000),
    "rul_hours": np.random.uniform(0, 1440, size=1000),
    "fault_type": np.random.choice(["normal", "cavitation", "bearing_wear", "overload"], size=1000),
    "is_running": np.ones(1000, dtype=int),
})
mixer_df.to_csv(os.path.join(syn_dir, "mixer_data.csv"), index=False)

# Compressor CSV
comp_df = pd.DataFrame({
    "timestamp": timestamps,
    "suction_pressure_bar": np.random.uniform(1.0, 2.5, size=1000),
    "discharge_pressure_bar": np.random.uniform(8.0, 11.0, size=1000),
    "discharge_temperature_C": np.random.uniform(50, 90, size=1000),
    "vibration_DE_rms_mm_s": np.random.uniform(0.5, 11.5, size=1000),
    "vibration_NDE_rms_mm_s": np.random.uniform(0.5, 5.5, size=1000),
    "motor_current_A": np.random.uniform(10.0, 25.0, size=1000),
    "efficiency_pct": np.random.uniform(80, 95, size=1000),
    "health_state": np.random.choice(["normal", "degrading", "fault"], size=1000),
    "rul_hours": np.random.uniform(0, 2160, size=1000),
    "fault_type": np.random.choice(["normal", "bearing_wear", "overload", "cavitation"], size=1000),
    "is_running": np.ones(1000, dtype=int),
})
comp_df.to_csv(os.path.join(syn_dir, "compressor_data.csv"), index=False)

# Spray Dryer CSV
dryer_df = pd.DataFrame({
    "timestamp": timestamps,
    "inlet_air_temperature_C": np.random.uniform(180, 220, size=1000),
    "outlet_air_temperature_C": np.random.uniform(70, 110, size=1000),
    "feed_flow_rate_lph": np.random.uniform(500, 1000, size=1000),
    "atomizer_speed_rpm": np.random.uniform(15000, 20000, size=1000).astype(int),
    "chamber_pressure_Pa": np.random.uniform(-30, -10, size=1000),
    "exhaust_humidity_pct": np.random.uniform(2.0, 10.0, size=1000),
    "heat_exchanger_efficiency": np.random.uniform(70, 92, size=1000),
    "health_state": np.random.choice(["normal", "degrading", "fault"], size=1000),
    "rul_hours": np.random.uniform(0, 2160, size=1000),
    "fault_type": np.random.choice(["normal", "cavitation", "overload", "bearing_wear"], size=1000),
    "is_running": np.ones(1000, dtype=int),
})
dryer_df.to_csv(os.path.join(syn_dir, "spray_dryer_data.csv"), index=False)

print("All mock models, processed files, and synthetic CSVs generated successfully!")
