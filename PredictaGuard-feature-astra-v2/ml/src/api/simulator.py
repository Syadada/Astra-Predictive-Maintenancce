"""
PredictaGuard API — Live equipment simulator.
Walks through preprocessed test windows from SKAB and CMAPSS datasets
to produce realistic live model predictions for the dashboard.
Synthetic Kerry CSVs are used for sensor value display (sparklines).
"""
import os
import math
import random
import numpy as np
import pandas as pd

from src.api.schemas import (
    EquipmentItem, EquipmentStatusResponse, KPIs,
    AlertItem, AlertsResponse, AlertSummary, FeatureImpact,
    SimulateStepResponse,
)



# Equipment configuration

_EQUIPMENT_CFG = [
    {
        "id": "ASTRA-MTR-101",
        "name": "Motor M-101 (Conveyor Drive)",
        "location": "Line 1 Packaging",
        "type": "skab",
        "skab_offset": 0,
        "sparkline_col": "vibration_rms_mm_s",
        "alert_unit": "mm/s",
        "alert_threshold": 8.5,
        "alert_scale": 15.0,  # multiply anomaly score to get "sensor value" in unit
    },
    {
        "id": "ASTRA-MTR-204",
        "name": "Motor M-204 (Cooling Fan)",
        "location": "Cooling Tower Section",
        "type": "skab",
        "skab_offset": 78,
        "sparkline_col": "vibration_rms_x_mm_s",
        "alert_unit": "A",
        "alert_threshold": 38.0,
        "alert_scale": 12.0,
    },
    {
        "id": "ASTRA-MTR-300",
        "name": "Motor M-300 (Water Pump)",
        "location": "Utility Station",
        "type": "cmapss",
        "cmapss_start": 9700,
        "hours_per_cycle": 1.0,
        "sparkline_col": "vibration_DE_rms_mm_s",
        "alert_unit": "mm/s",
        "alert_threshold": 10.0,
        "alert_scale": 20.0,
    },
    {
        "id": "ASTRA-MTR-305",
        "name": "Motor M-305 (Air Compressor)",
        "location": "Compressor Station",
        "type": "cmapss",
        "cmapss_start": 100,
        "hours_per_cycle": 40.0,
        "sparkline_col": "outlet_air_temperature_C",
        "alert_unit": "°C",
        "alert_threshold": 190.0,
        "alert_scale": 20.0,
    },
]

_FAULT_RECOMMENDATIONS = {
    "vibration": [
        "Throttle motor output to 60% immediately.",
        "Inspect motor bearing housing and mounting bolts.",
        "Schedule thermal imaging for motor coupling.",
    ],
    "current": [
        "Inspect rotor blades for misalignment or obstruction.",
        "Check bearing lubrication on main drive shaft.",
        "Schedule predictive motor maintenance within 48 hours.",
    ],
    "temperature": [
        "Reduce motor load / speed to 70% immediately.",
        "Verify cooling fan damper position and airflow.",
        "Log deviation event in CMMS maintenance system.",
    ],
    "rul": [
        "Plan controlled motor shutdown within current shift.",
        "Pre-stage replacement bearings and seals.",
        "Notify Reliability Engineer for immediate review.",
    ],
}

_SHAP_FEATURE_NAMES = {
    "skab": [
        {"name": "Radial Vibration",    "impact": 0.72},
        {"name": "Stator Current",       "impact": 0.18},
        {"name": "Process Temperature",  "impact": 0.10},
    ],
    "cmapss": [
        {"name": "Core Speed Drift",     "impact": 0.61},
        {"name": "HPC Temperature Rise", "impact": 0.28},
        {"name": "Pressure Ratio Loss",  "impact": 0.11},
    ],
}


class Simulator:
    def __init__(self, predictor, ml_dir: str, data_dir: str, db_manager=None):
        """
        predictor  : Predictor instance (already initialised)
        ml_dir     : path to d:/Kerry/ml/
        data_dir   : path to d:/Kerry/ml/data/
        """
        self.predictor = predictor
        self.db_manager = db_manager

        proc_dir = os.path.join(data_dir, "processed")
        syn_dir  = os.path.join(data_dir, "synthetic")

        # SKAB test windows (already scaler-transformed)
        skab_npz = np.load(os.path.join(proc_dir, "skab_windows.npz"))
        self._skab_X = skab_npz["X_test"]   # (234, 60, 8)
        self._skab_y = skab_npz["y_test"]   # (234,)
        self._n_skab = len(self._skab_X)

        # CMAPSS test windows (already scaler-transformed)
        cmapss_npz = np.load(os.path.join(proc_dir, "cmapss_FD001.npz"))
        self._cmapss_X = cmapss_npz["X_test"]  # (10196, 30, 14)
        self._cmapss_y = cmapss_npz["y_test"]  # (10196,)
        self._n_cmapss = len(self._cmapss_X)

        # Synthetic CSVs for sparkline sensor display
        self._pump_df  = pd.read_csv(os.path.join(syn_dir, "pump_data.csv"))
        self._mixer_df = pd.read_csv(os.path.join(syn_dir, "mixer_data.csv"))
        self._comp_df  = pd.read_csv(os.path.join(syn_dir, "compressor_data.csv"))
        self._spray_df = pd.read_csv(os.path.join(syn_dir, "spray_dryer_data.csv"))

        self._syn_dfs = {
            "ASTRA-MTR-101":  self._pump_df,
            "ASTRA-MTR-204":  self._mixer_df,
            "ASTRA-MTR-300":  self._comp_df,
            "ASTRA-MTR-305":  self._spray_df,
        }

        # Start cursor at 0; SKAB test starts with anomaly windows (good for demo)
        self._cursor = 0
        self._syn_cursor = 60   # synthetic CSV row index (start with 60 rows of history)
        self._downtime_avoided = 32.4
        self._alert_counter = 0

    # ------------------------------------------------------------------
    def step(self) -> SimulateStepResponse:
        self._cursor += 1
        self._syn_cursor += 1
        if self._syn_cursor >= len(self._pump_df) - 1:
            self._syn_cursor = 60

        timestamp = self._pump_df.iloc[self._syn_cursor]["timestamp"]

        # Insert telemetry into SQLite DB for each machine to simulate field ingestion
        if self.db_manager:
            csv_mappings = {
                "ASTRA-MTR-101": (self._pump_df, "vibration_rms_mm_s", "stator_current_A", "bearing_temperature_C"),
                "ASTRA-MTR-204": (self._mixer_df, "vibration_rms_x_mm_s", "stator_current_A", "gearbox_temperature_C"),
                "ASTRA-MTR-300": (self._comp_df, "vibration_DE_rms_mm_s", "stator_current_A", "bearing_temperature_C"),
                "ASTRA-MTR-305": (self._spray_df, "vibration_rms_mm_s", "feed_pump_current_A", "outlet_air_temperature_C"),
            }
            for machine_id, (df, vib_col, cur_col, temp_col) in csv_mappings.items():
                row = df.iloc[self._syn_cursor]
                vib = float(row[vib_col]) if vib_col in row else 0.2
                cur = float(row[cur_col]) if cur_col in row else 1.2
                temp = float(row[temp_col]) if temp_col in row else 80.0
                flw = float(row["flow_rate_lpm"]) if "flow_rate_lpm" in row else 100.0
                
                # Ingestion through DB manager cleans and validates the data automatically
                self.db_manager.insert_telemetry(machine_id, vib, cur, temp, flw)

        return SimulateStepResponse(cursor=self._cursor, timestamp=str(timestamp))

    # ------------------------------------------------------------------
    def _skab_window(self, offset: int) -> np.ndarray:
        idx = (self._cursor + offset) % self._n_skab
        return self._skab_X[idx : idx + 1]   # (1, 60, 8)

    def _cmapss_window(self, start: int) -> np.ndarray:
        idx = (self._cursor + start) % self._n_cmapss
        return self._cmapss_X[idx : idx + 1]  # (1, 30, 14)

    def _sparkline(self, equip_id: str, col: str, n: int = 30) -> list[float]:
        if self.db_manager:
            history = self.db_manager.get_recent_history(equip_id, limit=n)
            # Map column name to DB key
            db_col_map = {
                "vibration_rms_mm_s": "vibration_rms",
                "vibration_rms_x_mm_s": "vibration_rms",
                "vibration_DE_rms_mm_s": "vibration_rms",
                "stator_current_A": "motor_current",
                "feed_pump_current_A": "motor_current",
                "bearing_temperature_C": "temperature",
                "gearbox_temperature_C": "temperature",
                "outlet_air_temperature_C": "temperature",
                "flow_rate_lpm": "flow_rate",
            }
            db_key = db_col_map.get(col, "vibration_rms")
            vals = [row[db_key] for row in history]
            if len(vals) < n:
                vals = [vals[0]] * (n - len(vals)) + vals if vals else [0.0] * n
            return [round(float(v), 4) for v in vals]
        else:
            df  = self._syn_dfs[equip_id]
            end = self._syn_cursor
            start = max(0, end - n)
            vals = df[col].iloc[start:end].tolist()
            # Pad with first value if window not full
            if len(vals) < n:
                vals = [vals[0]] * (n - len(vals)) + vals
            return [round(float(v), 4) for v in vals]

    # ------------------------------------------------------------------
    def get_equipment_status(self) -> EquipmentStatusResponse:
        items: list[EquipmentItem] = []
        skab_scores: list[float] = []
        rul_hours_list: list[int] = []

        for cfg in _EQUIPMENT_CFG:
            if cfg["type"] == "skab":
                window = self._skab_window(cfg["skab_offset"])
                anomaly_score = self.predictor.predict_anomaly_score(window)
                rul_hours = int(round(3000 * max(0.0, 1.0 - 2.5 * anomaly_score)))
                fault_class = "Anomaly Detected" if anomaly_score > 0.35 else "Normal"
                skab_scores.append(anomaly_score)
            else:
                window = self._cmapss_window(cfg["cmapss_start"])
                rul_cycles = self.predictor.predict_rul(window)
                rul_hours = int(round(rul_cycles * cfg["hours_per_cycle"]))
                anomaly_score = float(1.0 - min(rul_cycles / 125.0, 1.0))
                fault_class = "Degraded" if rul_cycles < 40 else "Normal"

            health_index = round(max(0.0, 1.0 - anomaly_score), 4)
            rul_hours_list.append(rul_hours)

            if anomaly_score > 0.65:
                status = "critical"
            elif anomaly_score > 0.35:
                status = "warning"
            else:
                status = "optimal"

            sparkline = self._sparkline(cfg["id"], cfg["sparkline_col"])

            items.append(EquipmentItem(
                id=cfg["id"],
                name=cfg["name"],
                location=cfg["location"],
                status=status,
                rul_hours=rul_hours,
                health_index=health_index,
                anomaly_score=round(anomaly_score, 4),
                fault_class=fault_class,
                sensor_sparkline=sparkline,
            ))

        # KPI aggregation
        all_scores = [e.anomaly_score for e in items]
        overall_health = int(round(np.mean([1 - s for s in all_scores]) * 100))
        at_risk        = sum(1 for s in all_scores if s > 0.35)
        pred_failures  = sum(1 for h in rul_hours_list if h < 48)

        # Slowly accumulate downtime_avoided when equipment is healthy
        healthy_fraction = sum(1 for s in all_scores if s < 0.25) / len(all_scores)
        self._downtime_avoided = round(self._downtime_avoided + healthy_fraction * 0.02, 1)

        return EquipmentStatusResponse(
            kpis=KPIs(
                overall_health=overall_health,
                at_risk=at_risk,
                predicted_failures=pred_failures,
                downtime_avoided_h=self._downtime_avoided,
            ),
            equipment=items,
        )

    # ------------------------------------------------------------------
    def get_alerts(self) -> AlertsResponse:
        status = self.get_equipment_status()
        alerts: list[AlertItem] = []

        # Standard Model-Based Alerts
        for i, (equip, cfg) in enumerate(zip(status.equipment, _EQUIPMENT_CFG)):
            score = equip.anomaly_score

            if score > 0.65:
                severity = "critical"
            elif score > 0.35:
                severity = "warning"
            else:
                severity = None

            if severity:
                equip_type = cfg["type"]
                feat_names = _SHAP_FEATURE_NAMES[equip_type]
                features = [
                    FeatureImpact(
                        name=f["name"],
                        impact=round(f["impact"] * (0.8 + score * 0.4), 2),
                        color="red" if f["impact"] > 0.5 else ("amber" if f["impact"] > 0.2 else "muted"),
                    )
                    for f in feat_names
                ]

                # Sensor value estimate for display
                sensor_value = round(cfg["alert_threshold"] * (0.8 + score * 0.7), 1)
                minutes_ago = max(1, 30 - i * 7)   # stagger for realism

                rec_type = "vibration" if equip_type == "skab" else "rul"
                if equip_type == "skab" and "Cooling Fan" in equip.name:
                    rec_type = "current"
                if equip_type == "cmapss" and "Air Compressor" in equip.name:
                    rec_type = "temperature"

                title_map = {
                    "vibration": "Vibration Anomaly Detected",
                    "current":   "Motor Current Anomaly",
                    "temperature": "Motor Winding Temp Elevation",
                    "rul":       "Critical RUL Threshold Breached",
                }

                self._alert_counter += 1
                alerts.append(AlertItem(
                    id=f"ALT-{self._alert_counter:04d}",
                    severity=severity,
                    asset_id=equip.id,
                    asset_name=equip.name,
                    title=title_map[rec_type],
                    value=sensor_value,
                    unit=cfg["alert_unit"],
                    threshold=cfg["alert_threshold"],
                    minutes_ago=minutes_ago,
                    confidence=round(min(0.99, 0.70 + score * 0.35), 2),
                    feature_impacts=features,
                    recommendations=_FAULT_RECOMMENDATIONS[rec_type],
                ))

            # Database Ingestion & Rule-Based Checks (Sir Ronny feedback + flatline + 80C spike checks)
            if self.db_manager:
                history = self.db_manager.get_recent_history(cfg["id"], limit=5)
                if history:
                    temps = [h["temperature"] for h in history]
                    latest_temp = temps[-1]
                    
                    from src.api.notifier import trigger_alert_notifications
                    
                    # Rule 1: Flatline Sensor Check (at least 5 readings, all equal)
                    is_flatline = False
                    if len(temps) >= 5 and all(t == temps[0] for t in temps):
                        is_flatline = True
                        trigger_alert_notifications(
                            machine_id=equip.id,
                            alert_type="flatline",
                            title="Sensor Flatline / Lock Alert",
                            details=f"The last 5 temperature values on {equip.name} were identical ({latest_temp}°C). The sensor is locked."
                        )
                        
                    # Rule 2: High Temperature Limit Check (temperature > 80°C)
                    is_high_temp = latest_temp > 80.0
                    if is_high_temp:
                        trigger_alert_notifications(
                            machine_id=equip.id,
                            alert_type="temperature",
                            title="High Motor Temperature Alert (>80°C)",
                            details=f"The latest winding temperature on {equip.name} is {latest_temp}°C, exceeding the 80°C safe threshold."
                        )
                        
                    if is_flatline:
                        self._alert_counter += 1
                        alerts.append(AlertItem(
                            id=f"ALT-FLT-{self._alert_counter:04d}",
                            severity="critical",
                            asset_id=equip.id,
                            asset_name=equip.name,
                            title="Sensor Flatline / Lock Alert",
                            value=latest_temp,
                            unit="°C",
                            threshold=0.0,
                            minutes_ago=1,
                            confidence=0.99,
                            feature_impacts=[FeatureImpact(name="Sensor Stability", impact=1.0, color="red")],
                            recommendations=[
                                "Inspect sensor connections and wiring immediately.",
                                "Re-calibrate the temperature transmitter node.",
                                "Verify sensor loop current to resolve channel locking."
                            ],
                        ))
                        
                    if is_high_temp:
                        self._alert_counter += 1
                        alerts.append(AlertItem(
                            id=f"ALT-TMP-{self._alert_counter:04d}",
                            severity="critical",
                            asset_id=equip.id,
                            asset_name=equip.name,
                            title="High Motor Temperature Alert (>80°C)",
                            value=latest_temp,
                            unit="°C",
                            threshold=80.0,
                            minutes_ago=1,
                            confidence=0.95,
                            feature_impacts=[FeatureImpact(name="Winding Heat Load", impact=0.85, color="red")],
                            recommendations=[
                                "Reduce motor load/speed immediately to prevent stator damage.",
                                "Verify cooling fan operation and clean stator ventilation fins.",
                                "Log deviation event in CMMS maintenance database."
                            ],
                        ))

        # Sort critical first
        alerts.sort(key=lambda a: (0 if a.severity == "critical" else 1))

        n_crit = sum(1 for a in alerts if a.severity == "critical")
        n_warn = sum(1 for a in alerts if a.severity == "warning")

        return AlertsResponse(
            summary=AlertSummary(critical=n_crit, warning=n_warn),
            alerts=alerts,
        )
