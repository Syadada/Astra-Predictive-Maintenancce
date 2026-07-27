"""
PredictaGuard API — Model inference wrapper.
Loads all 3 trained models + scalers at startup and exposes inference methods.
"""
import os
import warnings
import joblib
import numpy as np
import shap

warnings.filterwarnings("ignore")

from src.api.schemas import (
    InferenceResponse, SHAPValues,
    HistoricalMatch, RecommendationDetail, CCPAlert,
)


_CWRU_FEATURE_NAMES = ["max", "min", "mean", "sd", "rms", "skewness", "kurtosis", "crest", "form"]
_NORMAL_CLASS = "Normal_1"

# Class mean feature vectors from the CWRU dataset (order: max min mean sd rms skew kurt crest form).
# Interpolating between these endpoints maps the slider range to bearing health states.
_CWRU_NORMAL_MEANS = [0.2051, -0.2065, 0.0125, 0.0650, 0.0663, -0.1731, -0.0956, 3.094,   5.529]
_CWRU_FAULT_MEANS  = [4.8273, -4.8405, 0.0121, 1.0566, 1.0564,  0.0716,  3.8953, 4.5911, 92.053]

# Severity weights for each CWRU class — used to compute a continuous anomaly score
# from the probability distribution rather than a binary 0/1 flag.
_FAULT_SEVERITY = {
    "Normal_1":   0.00,
    "Ball_007_1": 0.25,
    "OR_014_6_1": 0.30,
    "Ball_014_1": 0.40,
    "Ball_021_1": 0.50,
    "IR_007_1":   0.60,
    "IR_014_1":   0.65,
    "IR_021_1":   0.80,
    "OR_007_6_1": 0.85,
    "OR_021_6_1": 0.95,
}

_HISTORICAL_MATCHES: dict = {
    "OR_007_6_1": {"date": "2024-02-10", "similarity": 0.87, "failure_type": "Outer race fault — bearing replacement", "rul_at_event": 48},
    "OR_014_6_1": {"date": "2024-03-22", "similarity": 0.82, "failure_type": "Outer race fault — progressive spalling", "rul_at_event": 36},
    "OR_021_6_1": {"date": "2023-11-15", "similarity": 0.91, "failure_type": "Severe outer race damage — emergency shutdown", "rul_at_event": 18},
    "IR_007_1":   {"date": "2024-01-08", "similarity": 0.79, "failure_type": "Inner race fatigue crack", "rul_at_event": 72},
    "IR_014_1":   {"date": "2023-09-03", "similarity": 0.84, "failure_type": "Inner race spalling — progressive", "rul_at_event": 36},
    "IR_021_1":   {"date": "2024-04-17", "similarity": 0.93, "failure_type": "Severe inner race damage — seizure", "rul_at_event": 12},
    "Ball_007_1": {"date": "2024-05-05", "similarity": 0.76, "failure_type": "Ball element micro-pitting", "rul_at_event": 96},
    "Ball_014_1": {"date": "2023-08-20", "similarity": 0.81, "failure_type": "Ball element spalling", "rul_at_event": 60},
    "Ball_021_1": {"date": "2024-06-01", "similarity": 0.88, "failure_type": "Severe ball element damage", "rul_at_event": 24},
}

_RECOMMENDATION_DETAILS: dict = {
    "Normal_1":   {"action": "Continue monitoring — no action required", "part_number": "N/A", "cost_if_ignored_usd": 0, "downtime_hours": 0, "maintenance_window": "N/A"},
    "OR_007_6_1": {"action": "Replace outer race bearing assembly on motor shaft", "part_number": "MTR-101-OR7", "cost_if_ignored_usd": 2500, "downtime_hours": 4, "maintenance_window": "Tomorrow 22:00–02:00 UTC"},
    "OR_014_6_1": {"action": "Emergency bearing replacement — motor outer race", "part_number": "MTR-101-OR14", "cost_if_ignored_usd": 8000, "downtime_hours": 8, "maintenance_window": "Tonight 20:00–04:00 UTC"},
    "OR_021_6_1": {"action": "IMMEDIATE shutdown — severe motor outer race damage", "part_number": "MTR-101-OR21", "cost_if_ignored_usd": 35000, "downtime_hours": 24, "maintenance_window": "NOW"},
    "IR_007_1":   {"action": "Schedule motor inner race inspection and lubrication", "part_number": "MTR-101-IR7", "cost_if_ignored_usd": 3000, "downtime_hours": 5, "maintenance_window": "Within 72h"},
    "IR_014_1":   {"action": "Replace motor inner race bearing set", "part_number": "MTR-101-IR14", "cost_if_ignored_usd": 12000, "downtime_hours": 10, "maintenance_window": "Within 36h"},
    "IR_021_1":   {"action": "EMERGENCY: Controlled shutdown — motor inner race failure imminent", "part_number": "MTR-101-IR21", "cost_if_ignored_usd": 50000, "downtime_hours": 32, "maintenance_window": "NOW"},
    "Ball_007_1": {"action": "Re-lubricate and inspect motor ball elements", "part_number": "LUB-023-BLT", "cost_if_ignored_usd": 1800, "downtime_hours": 2, "maintenance_window": "Within 96h"},
    "Ball_014_1": {"action": "Replace motor ball element bearing set", "part_number": "MTR-101-BLT14", "cost_if_ignored_usd": 7500, "downtime_hours": 6, "maintenance_window": "Within 60h"},
    "Ball_021_1": {"action": "Emergency bearing replacement — motor ball element", "part_number": "MTR-101-BLT21", "cost_if_ignored_usd": 25000, "downtime_hours": 16, "maintenance_window": "Within 24h"},
}

_CCP_RULES: dict = {
    "minimal":  {"is_ccp": False, "ccp_type": "N/A",             "priority": "NORMAL"},
    "elevated": {"is_ccp": True,  "ccp_type": "Mixing Motor",    "priority": "HIGH"},
    "critical": {"is_ccp": True,  "ccp_type": "Pasteurisation Motor", "priority": "CRITICAL"},
}

_COPILOT_TEXTS = {
    "minimal": (
        "System is operating within calibrated parameters. "
        "Current vibration harmonics suggest healthy bearing lubrication. "
        "No action required."
    ),
    "elevated": (
        "Anomaly detected in motor current vs vibration pattern. "
        "Potential bearing fatigue developing. "
        "Recommend visual inspection and lubrication check within 48 hours."
    ),
    "critical": (
        "CRITICAL: High-frequency vibration with abnormal kurtosis signature detected. "
        "Pattern matches bearing seizure onset (CCP Rule 04). "
        "Recommended: Immediate controlled shutdown and emergency inspection."
    ),
}


class Predictor:
    def __init__(self, ml_dir: str):
        model_dir = os.path.join(ml_dir, "models")
        proc_dir  = os.path.join(ml_dir, "data", "processed")

        self.skab_model   = joblib.load(os.path.join(model_dir, "skab_best_model.joblib"))
        self.cwru_model   = joblib.load(os.path.join(model_dir, "cwru_best_model.joblib"))
        self.cwru_rf      = joblib.load(os.path.join(model_dir, "cwru_random_forest.joblib"))
        self.cmapss_model = joblib.load(os.path.join(model_dir, "cmapss_best_model.joblib"))

        self.skab_scaler   = joblib.load(os.path.join(proc_dir, "skab_scaler.joblib"))
        self.cwru_scaler   = joblib.load(os.path.join(proc_dir, "cwru_scaler.joblib"))
        self.cmapss_scaler = joblib.load(os.path.join(proc_dir, "cmapss_FD001_scaler.joblib"))

        self.le = joblib.load(os.path.join(proc_dir, "cwru_label_encoder.joblib"))
        self._normal_idx = list(self.le.classes_).index(_NORMAL_CLASS)

        # Real SHAP TreeExplainer — built from CWRU RF using training data background
        cwru_data = np.load(os.path.join(proc_dir, "cwru_features.npz"), allow_pickle=True)
        bg = self.cwru_scaler.transform(cwru_data["X_train"].astype(np.float64)[:200])
        self._shap_explainer = shap.TreeExplainer(
            self.cwru_rf, data=bg, feature_perturbation="interventional"
        )

        # CMAPSS baseline: sensor midpoints in raw sensor space (healthy ~30th percentile)
        sc = self.cmapss_scaler
        self._cmapss_base = sc.data_min_ + 0.30 * sc.data_range_  # (14,)

    # ------------------------------------------------------------------
    # Low-level helpers used by the simulator
    # ------------------------------------------------------------------

    def predict_anomaly_score(self, window_Nx60x8: np.ndarray) -> float:
        """window_Nx60x8: shape (N, 60, 8), already scaled by skab_scaler.
        Returns anomaly probability for the first window."""
        X = window_Nx60x8[:1].reshape(1, -1)
        proba = self.skab_model.predict_proba(X)[0, 1]
        return float(proba)

    def predict_rul(self, window_1x30x14: np.ndarray) -> float:
        """window_1x30x14: shape (1, 30, 14), already scaled by cmapss_scaler.
        Returns predicted RUL in cycles (0–125)."""
        X = window_1x30x14.reshape(1, -1).astype(np.float32)
        rul = float(self.cmapss_model.predict(X)[0])
        return max(0.0, rul)

    # ------------------------------------------------------------------
    # Interactive slider → real inference  (prediction.html)
    # ------------------------------------------------------------------

    def infer_from_sliders(
        self,
        vibration_rms: float,
        motor_current: float,
        temperature: float,
        flow_rate: float,
    ) -> InferenceResponse:
        """
        Map 4 UI slider values to CWRU 9 features + CMAPSS 30x14 window,
        run real models, return a fully populated InferenceResponse.
        """
        rms = float(vibration_rms)
        cur = float(motor_current)
        tmp = float(temperature)

        # --- CWRU 9 features from slider values ---
        # Interpolate between Normal_1 and OR_007_6_1 class-mean vectors.
        # A quadratic curve (deg²) keeps the feature near Normal_1 for the lower
        # half of the slider and accelerates toward the fault region in the upper half.
        _vib_min, _vib_max = 0.188, 0.60
        deg      = np.clip((rms - _vib_min) / (_vib_max - _vib_min), 0.0, 1.0)
        deg_soft = deg ** 2   # slower rise near the normal end

        features_raw = np.array(
            [n + deg_soft * (f - n) for n, f in zip(_CWRU_NORMAL_MEANS, _CWRU_FAULT_MEANS)],
            dtype=np.float64
        )
        # Motor current → extra kurtosis (overload increases bearing impact energy)
        cur_boost = (cur - 0.85) / (4.0 - 0.85)
        features_raw[6] += cur_boost * 8.0  # kurtosis index 6

        # Temperature → extra form factor (thermal stress alters signal characteristics)
        temp_boost = (tmp - 75.0) / (110.0 - 75.0)
        features_raw[8] += temp_boost * 6.0  # form factor index 8

        features_scaled = self.cwru_scaler.transform(features_raw.reshape(1, -1))

        # Fault class + probabilities
        proba       = self.cwru_model.predict_proba(features_scaled)[0]
        fault_idx   = int(np.argmax(proba))
        fault_class = self.le.classes_[fault_idx]
        fault_conf  = float(proba[fault_idx])

        # Severity-weighted anomaly score: continuous from 0 (normal) to 1 (severe fault).
        # More informative than the binary 1-P(Normal) because it distinguishes mild from
        # severe bearing faults even when both have high non-Normal probability.
        anomaly_score = float(sum(
            float(proba[i]) * _FAULT_SEVERITY.get(self.le.classes_[i], 0.0)
            for i in range(len(self.le.classes_))
        ))
        anomaly_score = min(max(anomaly_score, 0.0), 1.0)

        # High temperature override (>80°C Warning / >95°C Critical limit check)
        if tmp > 80.0:
            temp_anomaly = 0.35 + ((tmp - 80.0) / (110.0 - 80.0)) * 0.65
            anomaly_score = max(anomaly_score, temp_anomaly)
            if fault_class == "Normal_1":
                fault_class = "OR_014_6_1"  # Force a warning class if classified as normal

        # --- CMAPSS 30×14 window for RUL ---
        deg = np.clip((rms - 0.188) / (0.60 - 0.188), 0.0, 1.0)
        sc  = self.cmapss_scaler

        window_raw = np.tile(self._cmapss_base, (30, 1)).copy()  # (30, 14)
        # Add monotonic trend in temperature sensor (idx 2) and core speed (idx 7)
        for step in range(30):
            t_frac = step / 29.0
            window_raw[step, 2] = sc.data_min_[2] + (0.20 + 0.80 * deg * t_frac) * sc.data_range_[2]
            window_raw[step, 7] = sc.data_min_[7] + (0.20 + 0.80 * deg * t_frac) * sc.data_range_[7]
            # Also modulate inlet temperature (idx 0) with UI temperature slider
            window_raw[step, 0] = sc.data_min_[0] + (0.30 + 0.50 * (tmp - 75) / 35.0) * sc.data_range_[0]

        window_scaled = sc.transform(window_raw)                # (30, 14), values in [0,1]
        rul_cycles    = self.predict_rul(window_scaled.reshape(1, 30, 14))
        rul_hours     = int(round(rul_cycles * 24))

        # --- Real SHAP via TreeExplainer (CWRU RF, kelas yang diprediksi) ---
        # features_scaled: (1, 9) sudah dinormalisasi oleh cwru_scaler
        sv_raw = self._shap_explainer.shap_values(features_scaled)

        # SHAP 0.46+ mengembalikan ndarray (1, 9, n_classes); versi lama list
        if isinstance(sv_raw, np.ndarray) and sv_raw.ndim == 3:
            shap_vals = sv_raw[0, :, fault_idx]          # (9,) untuk kelas terprediksi
        else:
            shap_vals = sv_raw[fault_idx][0]             # fallback format lama

        abs_sv   = np.abs(shap_vals)
        sv_norm  = abs_sv / (abs_sv.sum() + 1e-9)       # (9,) normalised 0-1

        # Map 9 CWRU features → 4 UI groups
        # [max=0, min=1, mean=2, sd=3, rms=4, skewness=5, kurtosis=6, crest=7, form=8]
        sv_vib  = float(sv_norm[[0, 1, 4, 7]].sum())    # vibration: max, min, rms, crest
        sv_cur  = float(sv_norm[[3, 6]].sum())           # current:   sd, kurtosis
        sv_tmp  = float(sv_norm[[8]].sum())              # temperature: form_factor
        sv_flw  = float(sv_norm[[2, 5]].sum())           # flow:       mean, skewness

        total = sv_vib + sv_cur + sv_tmp + sv_flw + 1e-9
        shap = SHAPValues(
            vibration=round(sv_vib / total, 4),
            current=round(sv_cur / total, 4),
            temperature=round(sv_tmp / total, 4),
            flow=round(sv_flw / total, 4),
        )

        # Risk level thresholds
        if anomaly_score < 0.30:
            risk_level = "minimal"
        elif anomaly_score < 0.65:
            risk_level = "elevated"
        else:
            risk_level = "critical"

        # Historical match (only for non-normal fault classes)
        hist_data = _HISTORICAL_MATCHES.get(fault_class)
        historical_match = HistoricalMatch(**hist_data) if hist_data else None

        # Recommendation detail (fallback to Normal_1 if class not found)
        rec_data = _RECOMMENDATION_DETAILS.get(fault_class, _RECOMMENDATION_DETAILS["Normal_1"])
        recommendation_detail = RecommendationDetail(**rec_data)

        # CCP alert based on risk level
        ccp_data = _CCP_RULES[risk_level]
        ccp_alert = CCPAlert(**ccp_data)

        # Determine dominant driver feature for Copilot text
        drivers = {
            "vibration": shap.vibration,
            "current": shap.current,
            "temperature": shap.temperature,
            "flow": shap.flow,
        }
        # Align description text category with predicted bearing fault type, unless temperature spikes above 80°C
        if fault_class.startswith(("OR_", "IR_", "Ball_")):
            if tmp > 80.0:
                dominant_feature = "temperature"
            else:
                dominant_feature = "vibration"
        else:
            dominant_feature = max(drivers, key=drivers.get)
        
        # Build dynamic recommendation copilot text
        if risk_level == "minimal":
            recommendation = (
                "System is operating within calibrated parameters. "
                "All motor harmonics and thermal baselines suggest healthy state. "
                "No action required."
            )
        elif risk_level == "elevated":
            if dominant_feature == "temperature":
                recommendation = (
                    "Warning: Elevated motor winding temperature detected. "
                    "Suggest checking cooling ventilation and reducing motor speed."
                )
            elif dominant_feature == "current":
                recommendation = (
                    "Warning: Unbalanced stator current detected. "
                    "Suggest checking electrical terminal connections and stator phases."
                )
            elif dominant_feature == "flow":
                recommendation = (
                    "Warning: Inconsistent shaft speed vs load ratio. "
                    "Suggest verifying mechanical coupling alignment."
                )
            else:
                recommendation = (
                    "Warning: Elevated vibration levels detected. "
                    "Suggest inspecting motor mountings and checking bearing lubrication."
                )
        else: # critical
            if dominant_feature == "temperature":
                recommendation = (
                    "CRITICAL: Extreme motor winding heat buildup detected (>80°C limit breached). "
                    "Potential insulation failure or stator coil burn. Immediate controlled shutdown recommended."
                )
            elif dominant_feature == "current":
                recommendation = (
                    "CRITICAL: Phase-to-phase current imbalance exceeds safe tolerance. "
                    "Stator winding short imminent. Emergency shutdown required to prevent motor damage."
                )
            elif dominant_feature == "flow":
                recommendation = (
                    "CRITICAL: Severe shaft speed drop under constant voltage. "
                    "Mechanical rotor locking or shaft seizure onset. Immediate emergency shutdown required."
                )
            else:
                recommendation = (
                    "CRITICAL: Extreme high-frequency vibration amplitude detected. "
                    "Motor bearing degradation matches inner/outer race failure. Controlled shutdown required."
                )

        return InferenceResponse(
            anomaly_score=round(anomaly_score, 4),
            risk_level=risk_level,
            fault_class=fault_class,
            fault_confidence=round(fault_conf, 4),
            rul_cycles=int(round(rul_cycles)),
            rul_hours=rul_hours,
            recommendation=recommendation,
            shap_values=shap,
            historical_match=historical_match,
            recommendation_detail=recommendation_detail,
            ccp_alert=ccp_alert,
        )

    # ------------------------------------------------------------------
    # Model info (for /api/health)
    # ------------------------------------------------------------------

    @property
    def model_info(self) -> dict:
        return {
            "anomaly_detection": type(self.skab_model).__name__,
            "fault_classification": type(self.cwru_model).__name__,
            "rul_prediction": type(self.cmapss_model).__name__,
            "cwru_classes": list(self.le.classes_),
        }
