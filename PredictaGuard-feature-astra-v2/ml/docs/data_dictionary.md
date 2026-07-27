# PredictaGuard — Data Dictionary

All sensor statistics are derived from the actual dataset distributions used in this pipeline.

---

## 1. SKAB Dataset (Skoltech Anomaly Benchmark)

**Files**: `dataset/SCAB/anomaly-free/`, `dataset/SCAB/other/`, `dataset/SCAB/valve1/`, `dataset/SCAB/valve2/`  
**Format**: Semicolon-delimited CSV, 1-second sampling  
**Total rows**: 46,806  
**Source**: Skoltech water pump test rig, Feb–Mar 2020

| Column | Type | Unit | Range (approx) | Description |
|---|---|---|---|---|
| `datetime` | datetime | — | 2020-02-08 to 2020-03-09 | UTC timestamp, 1 Hz sampling |
| `Accelerometer1RMS` | float | g (RMS) | 0.016 – 0.723 | Pump housing vibration, axis 1 |
| `Accelerometer2RMS` | float | g (RMS) | 0.016 – 0.801 | Pump housing vibration, axis 2 |
| `Current` | float | A | 0.15 – 3.32 | Motor phase current |
| `Pressure` | float | bar | −1.26 – 1.69 | Differential pressure across valve |
| `Temperature` | float | °C | 65.1 – 95.0 | Water temperature |
| `Thermocouple` | float | °C | 22.0 – 33.4 | Ambient / bearing temperature |
| `Voltage` | float | V | 200.7 – 255.3 | Motor supply voltage |
| `Volume Flow RateRMS` | float | L/min (RMS) | 0.56 – 133.7 | Volumetric flow rate |
| `anomaly` | int | — | {0, 1} | 1 = anomalous condition (label) |
| `changepoint` | int | — | {0, 1} | 1 = structural change point |
| `source_category` | str | — | anomaly-free / other / valve1 / valve2 | Experiment type |

**Key statistics**:
- Anomaly rate (labelled files): **34.94%**
- Near-zero missing values (clean dataset)
- High correlation: Accelerometer1 ↔ Accelerometer2 (r=0.996), Temperature ↔ Flow Rate (r=0.913)
- Voltage is essentially independent of all other sensors

---

## 2. CWRU Bearing Dataset (Case Western Reserve University)

**File**: `dataset/CWRU/feature_time_48k_2048_load_1.csv`  
**Format**: CSV, pre-extracted time-domain features (2048-sample windows at 48 kHz)  
**Total rows**: 2,300 (230 per class, **perfectly balanced**)  
**Load condition**: 1 HP motor load

| Column | Type | Unit | Description |
|---|---|---|---|
| `max` | float | g | Maximum vibration amplitude in window |
| `min` | float | g | Minimum vibration amplitude in window |
| `mean` | float | g | Mean vibration in window |
| `sd` | float | g | Standard deviation of vibration |
| `rms` | float | g (RMS) | Root Mean Square — key fault indicator |
| `skewness` | float | — | Statistical skewness of window |
| `kurtosis` | float | — | Kurtosis — impulsiveness indicator |
| `crest` | float | — | Crest factor = max / rms |
| `form` | float | — | Form factor = rms / mean_abs |
| `fault` | str | — | Fault class label (see below) |

**Fault class labels**:

| Label | Description | Mean RMS |
|---|---|---|
| `Normal_1` | Healthy bearing | 0.066 |
| `Ball_007_1` | Ball fault, 0.007" diameter | 0.141 |
| `Ball_014_1` | Ball fault, 0.014" diameter | 0.138 |
| `Ball_021_1` | Ball fault, 0.021" diameter | 0.200 |
| `IR_007_1` | Inner race fault, 0.007" | 0.279 |
| `IR_014_1` | Inner race fault, 0.014" | 0.197 |
| `IR_021_1` | Inner race fault, 0.021" | 0.606 |
| `OR_007_6_1` | Outer race fault, 0.007" | 1.056 |
| `OR_014_6_1` | Outer race fault, 0.014" | 0.136 |
| `OR_021_6_1` | Outer race fault, 0.021" | 0.603 |

**PCA separability**: PC1+PC2 explain **80.0%** of variance; faults are well-separated in PC1 (RMS/amplitude factor) vs PC2 (shape/impulsiveness factor).

---

## 3. NASA CMAPSS Dataset

**Files**: `dataset/CMaps/train_FD00{1-4}.txt`, `test_FD00{1-4}.txt`, `RUL_FD00{1-4}.txt`  
**Format**: Space-delimited, no header, 26 columns  
**Reference**: Saxena et al., "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08

| Column | Name | Type | Description |
|---|---|---|---|
| 1 | `unit` | int | Engine unit ID |
| 2 | `cycle` | int | Operational cycle number |
| 3 | `op_setting_1` | float | Altitude / flight condition |
| 4 | `op_setting_2` | float | Mach number |
| 5 | `op_setting_3` | float | Throttle resolver angle |
| 6–26 | `sensor_1–21` | float | Sensor measurements (see below) |

**Sensor index to measurement mapping** (approximate, from literature):

| Sensor | Physical Measurement | FD001 Near-Constant? |
|---|---|---|
| sensor_1 | Total temperature at fan inlet | YES — drop |
| sensor_2 | Total temperature at LPC outlet | informative |
| sensor_3 | Total temperature at HPC outlet | informative |
| sensor_4 | Total temperature at LPT outlet | informative |
| sensor_5 | Pressure at fan inlet | YES (FD001) — drop |
| sensor_6 | Total pressure at bypass-duct | YES (FD001) — drop |
| sensor_7 | Total pressure at HPC inlet | informative |
| sensor_8 | Physical fan speed | informative |
| sensor_9 | Physical core speed | informative |
| sensor_10 | Engine pressure ratio | YES (FD001) — drop |
| sensor_11 | Static pressure at HPC outlet | informative |
| sensor_12 | Fuel flow ratio | informative |
| sensor_13 | Physical fan speed (corrected) | informative |
| sensor_14 | Physical core speed (corrected) | informative |
| sensor_15 | Bypass ratio | informative |
| sensor_16 | Burner fuel-air ratio | YES (all) — drop |
| sensor_17 | Bleed enthalpy | informative |
| sensor_18 | Demanded fan speed | YES (FD001) — drop |
| sensor_19 | Demanded corrected fan speed | YES (FD001) — drop |
| sensor_20 | HPT coolant bleed | informative |
| sensor_21 | LPT coolant bleed | informative |

**Sub-dataset summary**:

| Split | Train engines | Test engines | Conditions | Fault modes | Mean test RUL |
|---|---|---|---|---|---|
| FD001 | 100 | 100 | 1 (sea level) | 1 (HPC degradation) | 75.5 cycles |
| FD002 | 260 | 259 | 6 | 1 (HPC degradation) | 81.2 cycles |
| FD003 | 100 | 100 | 1 (sea level) | 2 (HPC + Fan) | 75.3 cycles |
| FD004 | 249 | 248 | 6 | 2 (HPC + Fan) | 86.6 cycles |

**Preprocessing decisions**:
- RUL capped at **125 cycles** (piecewise linear label)
- Near-constant sensors dropped per-split before normalisation
- Min-max scaling (0–1) fit on training engines only
- Sliding window: **30 cycles**, stride 1

---

## 4. Synthetic Kerry Equipment Data

All files in `ml/data/synthetic/`. Each has **264,960 rows** (6 months, 1-minute resolution).  
Period: **2025-07-01 06:00 to 2026-01-01 06:00**.

### Shared columns (all equipment)

| Column | Type | Description |
|---|---|---|
| `timestamp` | datetime | 1-minute UTC timestamp |
| `health_state` | str | `normal` / `degrading` / `fault` |
| `rul_hours` | float | Remaining Useful Life in hours |
| `fault_type` | str | `normal` / `cavitation` / `bearing_wear` / `overload` / `seal_leak` |
| `is_running` | int | 1 = operating, 0 = planned shutdown |

**Health state thresholds**:
- `normal`: RUL > 168 hours (7 days)
- `degrading`: 24 < RUL ≤ 168 hours
- `fault`: RUL ≤ 24 hours

---

### 4a. Pump (`pump_data.csv`)

**Kerry context**: Centrifugal pump in dairy product transfer lines  
**Inspired by**: SKAB water pump sensor signatures

| Column | Unit | Normal Range | Fault Indicators |
|---|---|---|---|
| `flow_rate_lpm` | L/min | 200–260 | Drops in cavitation / seal leak |
| `inlet_pressure_bar` | bar | 1.3–1.8 | Drops in seal leak |
| `outlet_pressure_bar` | bar | 2.7–3.5 | Drops in cavitation |
| `motor_current_A` | A | 1.0–3.5 | Spikes in overload |
| `vibration_rms_mm_s` | mm/s | 0.3–3.5 | Spikes in cavitation + bearing wear |
| `temperature_C` | °C | 65–95 | Rises in bearing wear + overload |
| `motor_voltage_V` | V | 200–256 | Drops during some faults |

---

### 4b. Mixer (`mixer_data.csv`)

**Kerry context**: Industrial paddle mixer for dairy / food ingredient blending  
**Inspired by**: SKAB current, vibration, thermocouple signatures

| Column | Unit | Normal Range | Fault Indicators |
|---|---|---|---|
| `mixer_speed_rpm` | RPM | 110–160 | Drops in overload / bearing wear |
| `motor_current_A` | A | 1.0–3.5 | Spikes in overload |
| `vibration_rms_x_mm_s` | mm/s | 0.2–3.0 | Asymmetric spike in imbalance |
| `vibration_rms_y_mm_s` | mm/s | 0.1–2.8 | Elevated in bearing wear |
| `gearbox_temperature_C` | °C | 22–34 | Rises in overload + bearing wear |
| `process_viscosity_cP` | cP | 700–1200 | Inversely linked to speed |
| `power_kW` | kW | 0.3–0.9 | Spikes in overload |

---

### 4c. Compressor (`compressor_data.csv`)

**Kerry context**: Refrigeration compressor for cold storage  
**Inspired by**: CWRU bearing fault RMS signatures + CMAPSS monotonic degradation

| Column | Unit | Normal Range | Fault Indicators |
|---|---|---|---|
| `suction_pressure_bar` | bar | 1.5–2.1 | Drops in cavitation |
| `discharge_pressure_bar` | bar | 8.5–11.0 | Drops under degradation |
| `discharge_temperature_C` | °C | 68–80 | Rises with bearing wear / degradation |
| `vibration_DE_rms_mm_s` | mm/s | 1.0–2.0 | Increases monotonically with wear (CWRU Normal→IR_021 pattern) |
| `vibration_NDE_rms_mm_s` | mm/s | 0.8–1.6 | Increases with ball fault progression |
| `motor_current_A` | A | 16–21 | Rises in overload |
| `efficiency_pct` | % | 88–93 | Monotonic decline (CMAPSS s14 slope) |

---

### 4d. Spray Dryer (`spray_dryer_data.csv`)

**Kerry context**: Milk powder spray drying tower  
**Inspired by**: CMAPSS temperature profiles and efficiency degradation

| Column | Unit | Normal Range | Fault Indicators |
|---|---|---|---|
| `inlet_air_temperature_C` | °C | 185–215 | Rises in fouling event |
| `outlet_air_temperature_C` | °C | 88–100 | Rises in nozzle blockage + fouling |
| `feed_flow_rate_lph` | L/hr | 730–970 | Drops in nozzle blockage |
| `atomizer_speed_rpm` | RPM | 16,500–19,000 | Drops in atomizer wear |
| `chamber_pressure_Pa` | Pa | −33 to −18 | Changes with air flow imbalance |
| `exhaust_humidity_pct` | % | 4.0–8.0 | Rises with moisture / nozzle issues |
| `heat_exchanger_efficiency` | % | 85–92 | Monotonic decline with fouling |

---

## 5. Preprocessed Arrays

All files in `ml/data/processed/`.

| File | Contents | Shape (X_train) | dtype |
|---|---|---|---|
| `skab_windows.npz` | X_train/val/test, y_train/val/test | (1091, 60, 8) | float32, int32 |
| `cwru_features.npz` | X, y_multi, y_bin for all splits | (1609, 9) | float32, int32 |
| `cmapss_FD001.npz` | X_train/val/test, y (RUL), metadata | (15104, 30, 14) | float32 |
| `cmapss_FD002.npz` | " | (39513, 30, 20) | float32 |
| `cmapss_FD003.npz` | " | (18610, 30, 15) | float32 |
| `cmapss_FD004.npz` | " | (46317, 30, 20) | float32 |
| `skab_scaler.joblib` | StandardScaler fit on anomaly-free | — | — |
| `cwru_scaler.joblib` | StandardScaler fit on CWRU train | — | — |
| `cwru_label_encoder.joblib` | LabelEncoder (10-class) | — | — |
| `cmapss_FD00{1-4}_scaler.joblib` | MinMaxScaler per FD split | — | — |
