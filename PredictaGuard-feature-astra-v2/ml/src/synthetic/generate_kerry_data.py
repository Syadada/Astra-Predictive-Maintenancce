"""
Synthetic Kerry Manufacturing Data Generator.
Generates 6 months of 1-minute resolution operational data for 4 equipment types:
  - Pump          (inspired by SKAB: flow, pressure, current, vibration)
  - Mixer         (inspired by SKAB: vibration, current, temperature)
  - Compressor    (inspired by CWRU bearing + CMAPSS degradation)
  - Spray Dryer   (inspired by CMAPSS: temperature, pressure, efficiency)

Each CSV has: timestamp, sensor readings, health_state, rul_hours, fault_type.
Statistical properties are derived from real dataset distributions.

Run from ml/:  python src/synthetic/generate_kerry_data.py
"""

import os
import warnings
import glob
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# Paths

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "ml", "data", "synthetic")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_SEED  = 2026
RNG          = np.random.default_rng(RANDOM_SEED)

START_DATE   = pd.Timestamp("2025-07-01 06:00:00")
END_DATE     = pd.Timestamp("2026-01-01 06:00:00")
FREQ         = "1min"


# Utility helpers


def make_timeline() -> pd.DatetimeIndex:
    return pd.date_range(START_DATE, END_DATE, freq=FREQ, inclusive="left")


def circadian_load(timestamps: pd.DatetimeIndex, base: float = 1.0,
                   amplitude: float = 0.15) -> np.ndarray:
    """Sinusoidal load pattern: peaks at 10:00, troughs at 22:00."""
    hour = timestamps.hour.to_numpy(dtype=float) + timestamps.minute.to_numpy(dtype=float) / 60.0
    return base + amplitude * np.sin(2 * np.pi * (hour - 4) / 24)


def weekend_factor(timestamps: pd.DatetimeIndex,
                   weekday_load: float = 1.0,
                   weekend_load: float = 0.70) -> np.ndarray:
    return np.where(timestamps.dayofweek.to_numpy() < 5, weekday_load, weekend_load)


def planned_shutdowns(timestamps: pd.DatetimeIndex,
                      shutdown_days: list) -> np.ndarray:
    """Returns boolean mask True = equipment running."""
    date_arr = timestamps.normalize().to_numpy()
    mask = np.ones(len(timestamps), dtype=bool)
    for day in shutdown_days:
        day_np = np.datetime64(pd.Timestamp(day).date(), "D")
        mask &= date_arr.astype("datetime64[D]") != day_np
    return mask


def degradation_curve(n: int, rng: np.random.Generator,
                      start_rul_hours: float = 720.0,
                      noise_std: float = 2.0) -> np.ndarray:
    """Monotonically decreasing RUL with small Gaussian noise."""
    base = np.linspace(start_rul_hours, 0, n)
    noise = rng.normal(0, noise_std, n)
    return np.clip(base + noise, 0, start_rul_hours)


def health_state_from_rul(rul: np.ndarray,
                           degrading_threshold: float = 168.0,
                           fault_threshold: float = 24.0) -> list:
    states = []
    for r in rul:
        if r > degrading_threshold:
            states.append("normal")
        elif r > fault_threshold:
            states.append("degrading")
        else:
            states.append("fault")
    return states


def add_noise(signal: np.ndarray, noise_std: float,
              rng: np.random.Generator) -> np.ndarray:
    return signal + rng.normal(0, noise_std, len(signal))


def inject_fault_period(signal: np.ndarray, mask: np.ndarray,
                         multiplier: float = 1.0,
                         offset: float = 0.0) -> np.ndarray:
    """Scale/shift signal during fault periods indicated by boolean mask."""
    out = signal.copy()
    out[mask] = out[mask] * multiplier + offset
    return out


def fault_injection_schedule(n: int, rng: np.random.Generator,
                              n_faults: int = 4,
                              fault_duration_minutes: int = 180
                              ) -> tuple[np.ndarray, list]:
    """
    Returns boolean mask where True = fault active, and list of fault types.
    Faults are randomly placed, non-overlapping.
    """
    mask  = np.zeros(n, dtype=bool)
    types = ["normal"] * n

    available_starts = list(range(1000, n - fault_duration_minutes - 100, n // (n_faults + 1)))
    chosen_starts = rng.choice(available_starts, size=n_faults, replace=False)
    chosen_starts = sorted(chosen_starts)

    fault_names = ["cavitation", "bearing_wear", "overload", "seal_leak"]

    for i, start in enumerate(chosen_starts):
        end = min(start + fault_duration_minutes, n)
        mask[start:end] = True
        fname = fault_names[i % len(fault_names)]
        for j in range(start, end):
            types[j] = fname

    return mask, types


def load_skab_stats() -> dict:
    """Load SKAB anomaly-free segment to derive sensor statistics."""
    af_path = os.path.join(DATASET_ROOT, "SCAB", "anomaly-free", "anomaly-free.csv")
    df = pd.read_csv(af_path, sep=";")
    sensors = ["Accelerometer1RMS", "Accelerometer2RMS", "Current",
               "Pressure", "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"]
    return {col: {"mean": df[col].mean(), "std": df[col].std()} for col in sensors}


def load_skab_anomaly_stats() -> dict:
    """Load SKAB anomalous segments to derive fault signature deltas."""
    frames = []
    for cat in ["other", "valve1", "valve2"]:
        for f in sorted(glob.glob(os.path.join(DATASET_ROOT, "SCAB", cat, "*.csv"))):
            df = pd.read_csv(f, sep=";")
            frames.append(df[df["anomaly"] == 1])
    combined = pd.concat(frames, ignore_index=True)
    sensors = ["Accelerometer1RMS", "Accelerometer2RMS", "Current",
               "Pressure", "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"]
    return {col: {"mean": combined[col].mean(), "std": combined[col].std()} for col in sensors}


def load_cwru_fault_stats() -> dict:
    """Load CWRU RMS and kurtosis per fault class for bearing signatures."""
    df = pd.read_csv(os.path.join(DATASET_ROOT, "CWRU", "feature_time_48k_2048_load_1.csv"))
    df.columns = df.columns.str.strip().str.replace('"', '')
    for col in ["rms", "kurtosis", "crest"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.groupby("fault")[["rms", "kurtosis", "crest"]].mean().to_dict("index")


def load_cmapss_degradation() -> dict:
    """Load CMAPSS FD001 to extract mean degradation slope for informative sensors."""
    path = os.path.join(DATASET_ROOT, "CMaps", "train_FD001.txt")
    cols = (["unit", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)])
    df = pd.read_csv(path, sep=r"\s+", header=None, names=cols)
    # Informative sensors for FD001
    keep = ["s2", "s3", "s4", "s7", "s9", "s11", "s12", "s14", "s15", "s17", "s20", "s21"]
    # Compute per-engine normalised degradation slope (value at last 10% vs first 10%)
    slopes = {}
    for col in keep:
        early_vals = df.groupby("unit").apply(
            lambda g: g[col].iloc[:max(1, len(g)//10)].mean())
        late_vals  = df.groupby("unit").apply(
            lambda g: g[col].iloc[max(1, len(g)*9//10):].mean())
        delta = (late_vals - early_vals) / (early_vals.abs().replace(0, 1))
        slopes[col] = delta.mean()
    return slopes



# Equipment generators


def generate_pump(timestamps: pd.DatetimeIndex,
                  skab_stats: dict, skab_fault: dict) -> pd.DataFrame:
    """
    Kerry pump: centrifugal pump in dairy processing.
    Sensors mapped from SKAB:
      flow_rate_lpm       <- Volume Flow RateRMS * 3.0
      inlet_pressure_bar  <- Pressure * 2.0 + 1.5
      outlet_pressure_bar <- Pressure * 4.0 + 3.0
      motor_current_A     <- Current
      vibration_rms_mm_s  <- Accelerometer1RMS * 12.0
      temperature_C       <- Temperature
      motor_voltage_V     <- Voltage
    """
    n = len(timestamps)
    load = circadian_load(timestamps) * weekend_factor(timestamps)

    # Planned shutdowns: 2 weeks during the period (approx)
    shutdown_days = ["2025-12-25", "2025-12-26", "2026-01-01"]
    running = planned_shutdowns(timestamps, shutdown_days)

    # Fault schedule
    fault_mask, fault_types = fault_injection_schedule(n, RNG, n_faults=4,
                                                        fault_duration_minutes=180)

    # RUL — 4 lifecycle epochs across 6 months
    segment_len = n // 4
    rul = np.concatenate([
        degradation_curve(segment_len, RNG, start_rul_hours=720, noise_std=1.5),
        degradation_curve(n - 3*segment_len + segment_len, RNG, start_rul_hours=720, noise_std=1.5),
        degradation_curve(segment_len, RNG, start_rul_hours=720, noise_std=1.5),
        degradation_curve(segment_len, RNG, start_rul_hours=720, noise_std=1.5),
    ])[:n]

    # Scale SKAB stats to Kerry pump units
    sf = skab_stats
    af = skab_fault

    flow_base   = sf["Volume Flow RateRMS"]["mean"] * 3.0
    flow_std    = sf["Volume Flow RateRMS"]["std"]  * 3.0
    in_p_base   = sf["Pressure"]["mean"] * 2.0 + 1.5
    in_p_std    = sf["Pressure"]["std"]  * 2.0
    out_p_base  = sf["Pressure"]["mean"] * 4.0 + 3.0
    out_p_std   = sf["Pressure"]["std"]  * 4.0
    curr_base   = sf["Current"]["mean"]
    curr_std    = sf["Current"]["std"]
    vib_base    = sf["Accelerometer1RMS"]["mean"] * 12.0
    vib_std     = sf["Accelerometer1RMS"]["std"]  * 12.0
    temp_base   = sf["Temperature"]["mean"]
    temp_std    = sf["Temperature"]["std"]
    volt_base   = sf["Voltage"]["mean"]
    volt_std    = sf["Voltage"]["std"]

    flow_rate   = add_noise(np.full(n, flow_base)  * load, flow_std,  RNG)
    in_press    = add_noise(np.full(n, in_p_base)  * load, in_p_std,  RNG)
    out_press   = add_noise(np.full(n, out_p_base) * load, out_p_std, RNG)
    motor_curr  = add_noise(np.full(n, curr_base)  * load, curr_std,  RNG)
    vibration   = add_noise(np.full(n, vib_base)   * load, vib_std,   RNG)
    temperature = add_noise(np.full(n, temp_base),          temp_std,  RNG)
    voltage     = add_noise(np.full(n, volt_base),          volt_std,  RNG)

    # Cavitation fault: flow drops, vibration spikes, pressure differential collapses
    cavitation_mask = fault_mask & np.array([ft == "cavitation" for ft in fault_types])
    flow_rate  = inject_fault_period(flow_rate,  cavitation_mask, multiplier=0.55, offset=0)
    vibration  = inject_fault_period(vibration,  cavitation_mask, multiplier=2.8,  offset=0)
    out_press  = inject_fault_period(out_press,  cavitation_mask, multiplier=0.65, offset=0)

    # Bearing wear: vibration + temperature rise
    bearing_mask = fault_mask & np.array([ft == "bearing_wear" for ft in fault_types])
    vibration   = inject_fault_period(vibration,   bearing_mask, multiplier=2.2, offset=1.5)
    temperature = inject_fault_period(temperature, bearing_mask, multiplier=1.0, offset=6.0)

    # Overload: current spikes
    overload_mask = fault_mask & np.array([ft == "overload" for ft in fault_types])
    motor_curr  = inject_fault_period(motor_curr, overload_mask, multiplier=1.6, offset=0)
    temperature = inject_fault_period(temperature, overload_mask, multiplier=1.0, offset=4.0)

    # Seal leak: flow drops, pressure instability
    seal_mask = fault_mask & np.array([ft == "seal_leak" for ft in fault_types])
    flow_rate = inject_fault_period(flow_rate, seal_mask, multiplier=0.75, offset=0)
    in_press  = inject_fault_period(in_press,  seal_mask, multiplier=0.80, offset=0)

    # Zero out when not running
    for sig in [flow_rate, in_press, out_press, motor_curr, vibration]:
        sig[~running] = 0.0
    temperature[~running] = 20.0  # ambient
    voltage[~running]     = 0.0

    df = pd.DataFrame({
        "timestamp"         : timestamps,
        "flow_rate_lpm"     : np.clip(flow_rate,  0, None).round(3),
        "inlet_pressure_bar": np.clip(in_press,   0, None).round(4),
        "outlet_pressure_bar": np.clip(out_press, 0, None).round(4),
        "motor_current_A"   : np.clip(motor_curr, 0, None).round(4),
        "vibration_rms_mm_s": np.clip(vibration,  0, None).round(4),
        "temperature_C"     : temperature.round(2),
        "motor_voltage_V"   : np.clip(voltage,    0, None).round(2),
        "health_state"      : health_state_from_rul(rul),
        "rul_hours"         : np.clip(rul, 0, None).round(1),
        "fault_type"        : fault_types,
        "is_running"        : running.astype(int),
    })
    return df


def generate_mixer(timestamps: pd.DatetimeIndex,
                   skab_stats: dict) -> pd.DataFrame:
    """
    Kerry mixer: industrial paddle mixer for dairy/food blending.
    Sensors inspired by SKAB vibration + current dynamics.
      mixer_speed_rpm     <- derived from current / voltage
      motor_current_A     <- Current
      vibration_rms_x     <- Accelerometer1RMS * 10.0
      vibration_rms_y     <- Accelerometer2RMS * 10.0
      gearbox_temp_C      <- Thermocouple
      process_viscosity_cP<- derived from flow rate inverse
      power_kW            <- current * voltage / 1000
    """
    n = len(timestamps)
    load = circadian_load(timestamps, base=1.0, amplitude=0.12) * weekend_factor(timestamps)

    shutdown_days = ["2025-12-25", "2025-12-26"]
    running = planned_shutdowns(timestamps, shutdown_days)

    fault_mask, fault_types = fault_injection_schedule(n, RNG, n_faults=3,
                                                        fault_duration_minutes=120)

    segment_len = n // 3
    rul = np.concatenate([
        degradation_curve(segment_len, RNG, start_rul_hours=1440, noise_std=2.0),
        degradation_curve(segment_len, RNG, start_rul_hours=1440, noise_std=2.0),
        degradation_curve(n - 2*segment_len, RNG, start_rul_hours=1440, noise_std=2.0),
    ])[:n]

    sf = skab_stats
    curr_mean = sf["Current"]["mean"]
    curr_std  = sf["Current"]["std"]
    vib1_mean = sf["Accelerometer1RMS"]["mean"] * 10.0
    vib1_std  = sf["Accelerometer1RMS"]["std"]  * 10.0
    vib2_mean = sf["Accelerometer2RMS"]["mean"] * 10.0
    vib2_std  = sf["Accelerometer2RMS"]["std"]  * 10.0
    tc_mean   = sf["Thermocouple"]["mean"]
    tc_std    = sf["Thermocouple"]["std"]
    volt_mean = sf["Voltage"]["mean"]
    volt_std  = sf["Voltage"]["std"]

    motor_curr   = add_noise(np.full(n, curr_mean) * load,       curr_std, RNG)
    vib_x        = add_noise(np.full(n, vib1_mean) * load,       vib1_std, RNG)
    vib_y        = add_noise(np.full(n, vib2_mean) * load,       vib2_std, RNG)
    gearbox_temp = add_noise(np.full(n, tc_mean),                 tc_std,   RNG)
    voltage      = add_noise(np.full(n, volt_mean),               volt_std, RNG)

    # Speed derived from torque model (rpm proportional to voltage/current ratio at load)
    mixer_speed  = (voltage / np.clip(motor_curr, 0.5, None)) * 60.0 * load
    mixer_speed  = add_noise(mixer_speed, 5.0, RNG)

    # Viscosity inversely proportional to speed (thick product = slower)
    viscosity = 1200.0 / np.clip(mixer_speed, 10, None)
    viscosity = add_noise(viscosity, 20.0, RNG)

    power_kw = (motor_curr * voltage / 1000.0)

    # Imbalance fault: asymmetric vibration X vs Y
    imbalance_mask = fault_mask & np.array([ft == "cavitation" for ft in fault_types])
    vib_x = inject_fault_period(vib_x, imbalance_mask, multiplier=2.5, offset=0)

    # Overload fault: current spike + temperature
    overload_mask = fault_mask & np.array([ft == "overload" for ft in fault_types])
    motor_curr   = inject_fault_period(motor_curr,   overload_mask, multiplier=1.7, offset=0)
    gearbox_temp = inject_fault_period(gearbox_temp, overload_mask, multiplier=1.0, offset=8.0)
    power_kw     = inject_fault_period(power_kw,     overload_mask, multiplier=1.7, offset=0)

    # Bearing wear: vibration both axes + temperature
    bearing_mask = fault_mask & np.array([ft == "bearing_wear" for ft in fault_types])
    vib_x        = inject_fault_period(vib_x,        bearing_mask, multiplier=2.0, offset=0)
    vib_y        = inject_fault_period(vib_y,        bearing_mask, multiplier=2.0, offset=0)
    gearbox_temp = inject_fault_period(gearbox_temp, bearing_mask, multiplier=1.0, offset=5.0)

    for sig in [motor_curr, vib_x, vib_y, power_kw, mixer_speed]:
        sig[~running] = 0.0
    gearbox_temp[~running] = 20.0

    df = pd.DataFrame({
        "timestamp"           : timestamps,
        "mixer_speed_rpm"     : np.clip(mixer_speed,  0, None).round(1),
        "motor_current_A"     : np.clip(motor_curr,   0, None).round(4),
        "vibration_rms_x_mm_s": np.clip(vib_x,        0, None).round(4),
        "vibration_rms_y_mm_s": np.clip(vib_y,        0, None).round(4),
        "gearbox_temperature_C": gearbox_temp.round(2),
        "process_viscosity_cP": np.clip(viscosity,    0, None).round(1),
        "power_kW"            : np.clip(power_kw,     0, None).round(3),
        "health_state"        : health_state_from_rul(rul),
        "rul_hours"           : np.clip(rul, 0, None).round(1),
        "fault_type"          : fault_types,
        "is_running"          : running.astype(int),
    })
    return df


def generate_compressor(timestamps: pd.DatetimeIndex,
                         cwru_stats: dict,
                         cmapss_slopes: dict) -> pd.DataFrame:
    """
    Kerry compressor: refrigeration compressor in cold storage.
    Sensors inspired by CWRU bearing RMS signatures + CMAPSS degradation trajectory.
      suction_pressure_bar    <- CMAPSS s9 mapping
      discharge_pressure_bar  <- CMAPSS s3 mapping
      discharge_temperature_C <- CMAPSS s2 mapping
      vibration_DE_rms_mm_s   <- CWRU rms * 15.0 (drive-end)
      vibration_NDE_rms_mm_s  <- CWRU rms * 12.0 (non-drive-end)
      motor_current_A         <- load-dependent
      efficiency_pct          <- CMAPSS s14 degradation proxy
    """
    n = len(timestamps)
    load = circadian_load(timestamps, base=1.0, amplitude=0.10) * weekend_factor(timestamps, 1.0, 0.85)

    shutdown_days = ["2025-12-25"]
    running = planned_shutdowns(timestamps, shutdown_days)

    # RUL — 2 long maintenance cycles
    half = n // 2
    rul = np.concatenate([
        degradation_curve(half,     RNG, start_rul_hours=2160, noise_std=3.0),
        degradation_curve(n - half, RNG, start_rul_hours=2160, noise_std=3.0),
    ])[:n]

    # Progress along each lifecycle (0.0 = new, 1.0 = end of life)
    progress = np.concatenate([
        np.linspace(0, 1, half),
        np.linspace(0, 1, n - half)
    ])

    fault_mask, fault_types = fault_injection_schedule(n, RNG, n_faults=5,
                                                        fault_duration_minutes=240)

    # Bearing vibration baseline from CWRU Normal_1
    normal_rms  = cwru_stats.get("Normal_1", {}).get("rms", 0.066)
    ir_rms      = cwru_stats.get("IR_021_1", {}).get("rms", 0.606)
    ball_rms    = cwru_stats.get("Ball_021_1", {}).get("rms", 0.200)

    # Degradation: vibration increases monotonically as RUL decreases
    vib_de_base  = normal_rms * 15.0
    vib_de_degrad = vib_de_base * (1 + progress * (ir_rms / normal_rms - 1))
    vib_nde_base  = normal_rms * 12.0
    vib_nde_degrad = vib_nde_base * (1 + progress * (ball_rms / normal_rms - 1) * 0.8)

    vib_de  = add_noise(vib_de_degrad  * load, vib_de_base  * 0.05, RNG)
    vib_nde = add_noise(vib_nde_degrad * load, vib_nde_base * 0.04, RNG)

    # Efficiency degrades with time (CMAPSS s14 slope proxy)
    eff_slope = cmapss_slopes.get("s14", -0.02)
    efficiency = 92.0 + eff_slope * 40.0 * progress   # 92% → ~89% at EOL
    efficiency = add_noise(efficiency, 0.5, RNG)

    # Pressures: slightly degrading with time
    suc_press  = add_noise(np.full(n, 1.8) * load  * (1 - 0.03 * progress), 0.05, RNG)
    dis_press  = add_noise(np.full(n, 9.5) * load  * (1 - 0.05 * progress), 0.15, RNG)
    dis_temp   = add_noise(np.full(n, 72.0) * (1 + 0.08 * progress), 1.2, RNG)
    motor_curr = add_noise(np.full(n, 18.5) * load * (1 + 0.04 * progress), 0.5, RNG)

    # Fault injections
    bearing_mask = fault_mask & np.array([ft == "bearing_wear" for ft in fault_types])
    vib_de   = inject_fault_period(vib_de,   bearing_mask, multiplier=2.5, offset=0)
    vib_nde  = inject_fault_period(vib_nde,  bearing_mask, multiplier=2.2, offset=0)
    dis_temp = inject_fault_period(dis_temp, bearing_mask, multiplier=1.0, offset=8.0)

    overload_mask = fault_mask & np.array([ft == "overload" for ft in fault_types])
    motor_curr = inject_fault_period(motor_curr, overload_mask, multiplier=1.5, offset=0)
    dis_temp   = inject_fault_period(dis_temp,   overload_mask, multiplier=1.0, offset=5.0)

    cavitation_mask = fault_mask & np.array([ft == "cavitation" for ft in fault_types])
    suc_press  = inject_fault_period(suc_press,  cavitation_mask, multiplier=0.60, offset=0)
    vib_de     = inject_fault_period(vib_de,     cavitation_mask, multiplier=3.0,  offset=0)
    efficiency = inject_fault_period(efficiency, cavitation_mask, multiplier=0.85, offset=0)

    for sig in [vib_de, vib_nde, motor_curr, suc_press, dis_press]:
        sig[~running] = 0.0
    dis_temp[~running] = 20.0
    efficiency[~running] = 0.0

    df = pd.DataFrame({
        "timestamp"               : timestamps,
        "suction_pressure_bar"    : np.clip(suc_press,  0, None).round(4),
        "discharge_pressure_bar"  : np.clip(dis_press,  0, None).round(3),
        "discharge_temperature_C" : dis_temp.round(2),
        "vibration_DE_rms_mm_s"   : np.clip(vib_de,     0, None).round(4),
        "vibration_NDE_rms_mm_s"  : np.clip(vib_nde,    0, None).round(4),
        "motor_current_A"         : np.clip(motor_curr,  0, None).round(3),
        "efficiency_pct"          : np.clip(efficiency,  0, 100).round(2),
        "health_state"            : health_state_from_rul(rul),
        "rul_hours"               : np.clip(rul, 0, None).round(1),
        "fault_type"              : fault_types,
        "is_running"              : running.astype(int),
    })
    return df


def generate_spray_dryer(timestamps: pd.DatetimeIndex,
                          cmapss_slopes: dict) -> pd.DataFrame:
    """
    Kerry spray dryer: milk powder spray drying unit.
    Sensors inspired by CMAPSS temperature/pressure/efficiency degradation.
      inlet_air_temperature_C  <- high T (180-220 C)
      outlet_air_temperature_C <- lower T (80-100 C)
      feed_flow_rate_lph       <- feed pump flow
      atomizer_speed_rpm       <- rotary atomizer
      chamber_pressure_Pa      <- slight negative pressure
      exhaust_humidity_pct     <- outlet air humidity
      heat_exchanger_efficiency<- degrades with fouling
    """
    n = len(timestamps)
    load = circadian_load(timestamps, base=1.0, amplitude=0.08) * weekend_factor(timestamps)

    shutdown_days = ["2025-12-25", "2025-12-26", "2026-01-01"]
    running = planned_shutdowns(timestamps, shutdown_days)

    # Spray dryer: longer maintenance intervals (quarterly)
    quarter = n // 4
    rul = np.concatenate([
        degradation_curve(quarter,     RNG, start_rul_hours=2160, noise_std=5.0),
        degradation_curve(quarter,     RNG, start_rul_hours=2160, noise_std=5.0),
        degradation_curve(quarter,     RNG, start_rul_hours=2160, noise_std=5.0),
        degradation_curve(n-3*quarter, RNG, start_rul_hours=2160, noise_std=5.0),
    ])[:n]

    progress_all = []
    for i in range(4):
        seg = quarter if i < 3 else n - 3*quarter
        progress_all.append(np.linspace(0, 1, seg))
    progress = np.concatenate(progress_all)[:n]

    fault_mask, fault_types = fault_injection_schedule(n, RNG, n_faults=3,
                                                        fault_duration_minutes=360)

    # Inlet temperature: stable around 200°C
    inlet_temp   = add_noise(np.full(n, 200.0), 3.0, RNG) * load
    # Outlet temperature: controlled to 90°C; rises with fouling
    fouling_rise = 8.0 * progress   # outlet rises as heat exchanger fouls
    outlet_temp  = add_noise(np.full(n, 90.0) + fouling_rise, 1.5, RNG)
    # Feed flow
    feed_flow    = add_noise(np.full(n, 850.0) * load, 15.0, RNG)
    # Atomizer speed: stable, slight wear
    atomizer_spd = add_noise(np.full(n, 18000.0) * (1 - 0.02 * progress), 200.0, RNG)
    # Chamber pressure: slight negative (evaporative drying)
    chamber_press = add_noise(np.full(n, -25.0), 3.0, RNG)
    # Exhaust humidity: rises as product moisture increases (fouling indicator)
    exhaust_hum  = add_noise(np.full(n, 5.0) + 4.0 * progress, 0.4, RNG)
    # Heat exchanger efficiency degrades
    eff_slope = cmapss_slopes.get("s14", -0.02)
    hex_efficiency = add_noise(90.0 + eff_slope * 25.0 * progress, 0.8, RNG)

    # Nozzle blockage: feed flow drops → outlet temp rises
    nozzle_mask = fault_mask & np.array([ft == "cavitation" for ft in fault_types])
    feed_flow    = inject_fault_period(feed_flow,    nozzle_mask, multiplier=0.45, offset=0)
    outlet_temp  = inject_fault_period(outlet_temp,  nozzle_mask, multiplier=1.0, offset=12.0)
    exhaust_hum  = inject_fault_period(exhaust_hum,  nozzle_mask, multiplier=0.7, offset=0)

    # Fouling event: efficiency drops, outlet temp rises sharply
    fouling_mask = fault_mask & np.array([ft == "overload" for ft in fault_types])
    hex_efficiency = inject_fault_period(hex_efficiency, fouling_mask, multiplier=0.80, offset=0)
    outlet_temp    = inject_fault_period(outlet_temp,    fouling_mask, multiplier=1.0, offset=7.0)
    inlet_temp     = inject_fault_period(inlet_temp,     fouling_mask, multiplier=1.05, offset=0)

    # Atomizer wear: speed drops, vibration would rise (not modelled separately)
    atomizer_mask = fault_mask & np.array([ft == "bearing_wear" for ft in fault_types])
    atomizer_spd   = inject_fault_period(atomizer_spd,   atomizer_mask, multiplier=0.75, offset=0)
    exhaust_hum    = inject_fault_period(exhaust_hum,     atomizer_mask, multiplier=1.0, offset=3.0)

    for sig in [inlet_temp, outlet_temp, feed_flow, atomizer_spd]:
        sig[~running] = 0.0
    chamber_press[~running] = 0.0
    exhaust_hum[~running]   = 0.0
    hex_efficiency[~running] = 0.0

    df = pd.DataFrame({
        "timestamp"                  : timestamps,
        "inlet_air_temperature_C"    : np.clip(inlet_temp,   0, None).round(2),
        "outlet_air_temperature_C"   : np.clip(outlet_temp,  0, None).round(2),
        "feed_flow_rate_lph"         : np.clip(feed_flow,    0, None).round(1),
        "atomizer_speed_rpm"         : np.clip(atomizer_spd, 0, None).round(0).astype(int),
        "chamber_pressure_Pa"        : chamber_press.round(2),
        "exhaust_humidity_pct"       : np.clip(exhaust_hum,  0, 100).round(3),
        "heat_exchanger_efficiency"  : np.clip(hex_efficiency, 0, 100).round(2),
        "health_state"               : health_state_from_rul(rul),
        "rul_hours"                  : np.clip(rul, 0, None).round(1),
        "fault_type"                 : fault_types,
        "is_running"                 : running.astype(int),
    })
    return df



# Main


def print_summary(name: str, df: pd.DataFrame):
    print(f"\n  {name}")
    print(f"    Rows      : {len(df):,}")
    print(f"    Columns   : {list(df.columns)}")
    print(f"    Date range: {df['timestamp'].min()}  to  {df['timestamp'].max()}")
    hs = df["health_state"].value_counts()
    print(f"    Health states: {hs.to_dict()}")
    ft = df["fault_type"].value_counts()
    print(f"    Fault types  : {ft.to_dict()}")
    print(f"    RUL hours    : mean={df['rul_hours'].mean():.1f}  "
          f"min={df['rul_hours'].min()}  max={df['rul_hours'].max()}")


def run():
    print("=" * 60)
    print("  Kerry Synthetic Data Generator")
    print("=" * 60)

    print("\n[1] Loading source dataset statistics...")
    skab_stats   = load_skab_stats()
    skab_fault   = load_skab_anomaly_stats()
    cwru_stats   = load_cwru_fault_stats()
    cmapss_slopes = load_cmapss_degradation()
    print(f"    SKAB normal stats loaded  ({len(skab_stats)} sensors)")
    print(f"    SKAB fault stats loaded   ({len(skab_fault)} sensors)")
    print(f"    CWRU fault stats loaded   ({len(cwru_stats)} classes)")
    print(f"    CMAPSS slopes loaded      ({len(cmapss_slopes)} sensors)")

    print(f"\n[2] Generating timestamps ({START_DATE} to {END_DATE}, freq=1min)...")
    timestamps = make_timeline()
    print(f"    Total timesteps: {len(timestamps):,}")

    print("\n[3] Generating equipment data...")

    pump_df       = generate_pump(timestamps, skab_stats, skab_fault)
    mixer_df      = generate_mixer(timestamps, skab_stats)
    compressor_df = generate_compressor(timestamps, cwru_stats, cmapss_slopes)
    dryer_df      = generate_spray_dryer(timestamps, cmapss_slopes)

    print_summary("Pump",        pump_df)
    print_summary("Mixer",       mixer_df)
    print_summary("Compressor",  compressor_df)
    print_summary("Spray Dryer", dryer_df)

    print("\n[4] Saving CSV files...")
    equipment = {
        "pump_data.csv"        : pump_df,
        "mixer_data.csv"       : mixer_df,
        "compressor_data.csv"  : compressor_df,
        "spray_dryer_data.csv" : dryer_df,
    }
    for fname, df in equipment.items():
        out_path = os.path.join(OUTPUT_DIR, fname)
        df.to_csv(out_path, index=False)
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"    {fname:<30s}  {len(df):>8,} rows  {size_mb:.1f} MB")

    print("\n" + "="*60)
    print("  Synthetic Data Generation Complete")
    print(f"  Output: {OUTPUT_DIR}")
    print("="*60)


if __name__ == "__main__":
    run()
