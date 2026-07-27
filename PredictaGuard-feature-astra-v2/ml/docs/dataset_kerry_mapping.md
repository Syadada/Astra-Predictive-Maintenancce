# PredictaGuard — Dataset-to-Kerry Equipment Mapping

This document explains how the three source datasets map to Kerry Group manufacturing
equipment types, and the rationale for each signal mapping.

---

## Overview

| Kerry Equipment | Primary Dataset | Secondary Dataset | ML Task |
|---|---|---|---|
| Pump | SKAB | CWRU (bearing faults) | Anomaly detection |
| Mixer | SKAB | — | Anomaly detection |
| Compressor | CWRU | CMAPSS (RUL degradation) | Fault classification + RUL |
| Spray Dryer | CMAPSS | SKAB (flow/pressure) | RUL prediction |

---

## 1. SKAB → Pump & Mixer

**Why SKAB?**  
SKAB was collected on a water pump test rig and includes realistic sensor readings for rotating
machinery with valve-controlled flow paths. Kerry's pumps (CIP transfer pumps, dairy product
pumps) and mixers operate under similar physical principles: motor current, vibration, flow,
pressure, and temperature.

### Signal Mapping

| SKAB Signal | Kerry Pump Signal | Scale Factor | Rationale |
|---|---|---|---|
| `Volume Flow RateRMS` | `flow_rate_lpm` | × 3.0 | SKAB rig ≈ 75 L/min; Kerry pumps ≈ 220 L/min |
| `Pressure` | `inlet_pressure_bar` | × 2.0 + 1.5 | Differential → absolute; Kerry inlet ≈ 1.5–2.0 bar |
| `Pressure` | `outlet_pressure_bar` | × 4.0 + 3.0 | Kerry outlet head ≈ 3.0–3.5 bar |
| `Current` | `motor_current_A` | × 1.0 | Direct mapping; both ~1–3 A range |
| `Accelerometer1RMS` | `vibration_rms_mm_s` | × 12.0 | g → mm/s velocity equivalent |
| `Temperature` | `temperature_C` | × 1.0 | Both water-process temperature |
| `Voltage` | `motor_voltage_V` | × 1.0 | Both 230V single-phase |

| SKAB Signal | Kerry Mixer Signal | Scale Factor | Rationale |
|---|---|---|---|
| `Current` | `motor_current_A` | × 1.0 | Direct |
| `Accelerometer1RMS` | `vibration_rms_x_mm_s` | × 10.0 | Horizontal axis |
| `Accelerometer2RMS` | `vibration_rms_y_mm_s` | × 10.0 | Vertical axis |
| `Thermocouple` | `gearbox_temperature_C` | × 1.0 | Direct (ambient/bearing temp) |
| `Voltage` | (used in speed derivation) | — | Voltage/current ratio → RPM |
| `Volume Flow RateRMS` | `process_viscosity_cP` (inverse) | — | Higher flow = lower viscosity |

### Fault Signature Mapping (SKAB anomalies → Kerry faults)

| SKAB Anomaly Pattern | Kerry Pump Fault | Evidence |
|---|---|---|
| Flow rate drop + vibration spike | Cavitation | Valve-induced flow restriction in SKAB `other/` files |
| Vibration increase + temperature rise | Bearing wear | Progressive degradation pattern |
| Current spike (>1.6×) + temp rise | Motor overload | High-current events in SKAB labelled files |
| Pressure drop + flow reduction | Seal leak | Pressure differential collapse in SKAB valve2 |

---

## 2. CWRU → Compressor (and Pump bearing faults)

**Why CWRU?**  
CWRU bearing data provides quantitative vibration signatures for four bearing fault locations
(ball, inner race, outer race) at three severity levels (0.007", 0.014", 0.021" diameter).
Kerry's compressors use roller bearings subject to the same failure modes. The extracted
features (RMS, kurtosis, crest factor) directly parameterise the synthetic vibration model.

### Signal Mapping

| CWRU Feature | Kerry Compressor Signal | Mapping |
|---|---|---|
| `rms` (Normal_1 = 0.066g) | `vibration_DE_rms_mm_s` (baseline) | × 15.0 → 1.0 mm/s normal |
| `rms` (IR_021_1 = 0.606g) | `vibration_DE_rms_mm_s` (fault) | × 15.0 → 9.1 mm/s fault |
| `rms` (Ball_021_1 = 0.200g) | `vibration_NDE_rms_mm_s` (fault) | × 12.0 → 2.4 mm/s fault |
| `kurtosis` (Normal ≈ −0.10) | threshold for impulsive fault detection | Kurtosis > 3 → possible fault |
| `crest` (Normal ≈ 3.09) | alert threshold in production | Crest > 6 → bearing alarm |

### Degradation Trajectory

CWRU class ordering (Normal → Ball_007 → Ball_014 → Ball_021 → IR_021 → OR_021) maps
directly to increasing RUL consumption in the compressor:

| CWRU Fault Class | RUL Stage in Compressor | Expected RMS |
|---|---|---|
| Normal_1 | > 70% lifecycle remaining | ≈ 1.0 mm/s |
| Ball_007_1 | 60–70% remaining | ≈ 2.1 mm/s |
| Ball_021_1 | 40–60% remaining | ≈ 3.0 mm/s |
| IR_007_1 | 20–40% remaining | ≈ 4.2 mm/s |
| IR_021_1 / OR_021_1 | < 20% remaining | ≈ 6–15 mm/s |

---

## 3. CMAPSS → Compressor (RUL degradation) + Spray Dryer

**Why CMAPSS?**  
CMAPSS provides complete run-to-failure degradation trajectories for a turbofan engine.
The sensor profiles for temperature, pressure ratio, efficiency, and bleed valves have
direct physical analogues in a refrigeration compressor and spray dryer. The monotonic
efficiency decline and temperature drift are the primary signatures used.

### CMAPSS Sensor → Kerry Compressor Mapping

| CMAPSS Sensor | Measurement | Kerry Compressor Analogue |
|---|---|---|
| `sensor_9` | Physical core speed | `suction_pressure_bar` proxy (inversely linked) |
| `sensor_3` | HPC outlet temperature | `discharge_temperature_C` |
| `sensor_14` | LPT inlet temperature | `efficiency_pct` degradation slope |
| `sensor_11` | Static pressure at HPC | `discharge_pressure_bar` trend |

**Slope extraction**: Per-engine degradation slopes from CMAPSS FD001 are used to set
the rate of efficiency decline and temperature rise in the synthetic compressor model.
The mean `sensor_14` slope (≈ −2% per normalised lifecycle) translates to a −3% efficiency
drop over 2160 hours in the Kerry compressor.

### CMAPSS Sensor → Kerry Spray Dryer Mapping

| CMAPSS Sensor | Measurement | Kerry Spray Dryer Analogue | Scaling |
|---|---|---|---|
| `sensor_2` | Fan inlet temperature | `inlet_air_temperature_C` | × 0.31 + offset → 200°C range |
| `sensor_3` | HPC outlet temperature | `outlet_air_temperature_C` | → 90°C range |
| `sensor_14` | Corrected core speed | `heat_exchanger_efficiency` | Monotonic decline slope |
| `sensor_11` | Static pressure | `chamber_pressure_Pa` | → −25 Pa range |
| `sensor_15` | Bypass ratio | `exhaust_humidity_pct` | Proxy for air/feed ratio |

**Fouling model**: CMAPSS shows a monotonic efficiency decline with operational cycles.
The spray dryer heat exchanger fouling is modelled identically: efficiency declines linearly
from 90% to ~87% over a 2160-hour cycle, with step-change drops during active fouling events.

---

## 4. Kerry-Specific Additions (not in source datasets)

The following signals were synthesised from first principles for Kerry context realism,
without a direct SKAB/CWRU/CMAPSS analogue:

| Signal | Equipment | Basis |
|---|---|---|
| `process_viscosity_cP` | Mixer | Derived from speed/current ratio; dairy product rheology |
| `feed_flow_rate_lph` | Spray Dryer | Typical dairy concentrate feed rates (500–1000 L/hr) |
| `atomizer_speed_rpm` | Spray Dryer | Rotary atomizer specs: 15,000–20,000 RPM |
| `chamber_pressure_Pa` | Spray Dryer | Standard drying tower slight negative pressure (−20 to −30 Pa) |
| `circadian load pattern` | All | Sinusoidal daily load based on Kerry shift patterns |
| `weekend load reduction` | All | 70% load on weekends vs weekdays |
| `planned shutdowns` | All | Christmas/New Year shutdown dates (Dec 25, 26, Jan 1) |

---

## 5. Fault Type Definitions

| Fault Label | Affected Equipment | Physical Description | Source Analogue |
|---|---|---|---|
| `cavitation` | Pump, Compressor | Air entrainment → pressure collapse + vibration | SKAB valve-throttle events |
| `bearing_wear` | Pump, Mixer, Compressor | Progressive bearing race damage → vibration + heat | CWRU IR_021 / Ball_021 progression |
| `overload` | Pump, Mixer, Compressor | Excessive mechanical load → current + temperature spike | SKAB high-current anomalies |
| `seal_leak` | Pump | Mechanical seal failure → flow / pressure loss | SKAB valve2 pressure events |
| `nozzle_blockage` | Spray Dryer | Feed nozzle fouling → reduced flow + outlet temp rise | CMAPSS reduced mass flow |
| `fouling` | Spray Dryer | Heat exchanger deposit buildup → efficiency decline | CMAPSS monotonic degradation |
| `atomizer_wear` | Spray Dryer | Rotary atomizer disc wear → speed reduction | CWRU progressive fault model |

*Note: `cavitation` label in Spray Dryer CSV refers to nozzle blockage; `overload` refers to fouling; `bearing_wear` refers to atomizer wear. Renaming to descriptive labels is recommended before frontend integration.*

---

## 6. Recommended Kerry Equipment IDs (for dashboard integration)

| Equipment | Suggested ID | Location |
|---|---|---|
| Pump | `KERRY-PUMP-001` | CIP circuit, Building A |
| Mixer | `KERRY-MIX-001` | Ingredient blending, Building B |
| Compressor | `KERRY-COMP-001` | Cold storage, Building C |
| Spray Dryer | `KERRY-SD-001` | Powder production, Building D |
