import os
import sys
# pyrefly: ignore [missing-import]
import numpy as np
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, text

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.sequence import FEATURE_COLS


class DecisionEngine:
    """
    PredictaGuard Decision Engine — Full Alert Management Pipeline.

    Flow:
        AI Models
              │
              ▼
        DecisionEngine.decide()
              │
              ├── 1. Rule Validation          (SEVERITY_RULES)
              │
              ├── 2. Context Validation       (sensor fault, ambient, transient, etc.)
              │
              ├── 3. Multi-Signal Consensus   (2-of-3 voting: anomaly + health + RUL)
              │
              ├── 4. Persistence Check        (≥3 consecutive elevated windows)
              │
              ├── 5. False Alarm Suppression  (post-maintenance, load, shift, etc.)
              │
              ├── 6. Alert Tier Assignment    (none / dashboard_only / email / full)
              │
              └── Returns structured decision dict
    """

    def __init__(self, scaler_dir='models'):
        self.scaler_dir = scaler_dir

        # Setup Postgres database connection for historical persistence check
        DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
        DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
        DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
        DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
        DB_NAME = "astra_predictive_maintenance"

        self.engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

    # ─── Severity Level Ordering ─────────────────────────────────────────────
    # Used for comparing severity levels numerically (higher = more severe)
    _SEVERITY_RANK = {
        'NORMAL': 0,
        'WARNING': 1,
        'HIGH_WARNING': 2,
        'CRITICAL': 3,
    }

    # ─── Multi-Signal Consensus Thresholds ───────────────────────────────────
    # A severity upgrade is only valid if ≥2 of 3 signals agree.
    _CONSENSUS_THRESHOLDS = {
        # (anomaly_score_min, health_score_max, rul_days_max)
        'WARNING':      (0.55, 60.0, 10.0),
        'HIGH_WARNING': (0.65, 50.0, 7.0),
        'CRITICAL':     (0.80, 35.0, 4.0),
    }

    # ─── Initial Severity Rules ───────────────────────────────────────────────
    # Evaluated first to produce a raw severity before further filtering.
    SEVERITY_RULES = [
        # (condition_fn, severity, recommendation)
        (lambda a, h, r, ctx: a > 0.85 and h < 30, 'CRITICAL', 'Inspect immediately — shutdown risk'),
        (lambda a, h, r, ctx: r < 3, 'CRITICAL', 'Schedule emergency maintenance'),
        (lambda a, h, r, ctx: (a > 0.65 and h < 55) or r < 7, 'HIGH_WARNING', 'Plan maintenance this week'),
        (lambda a, h, r, ctx: a > 0.65 and ctx.get('load_level') == 'high', 'WARNING', 'Monitor closely — high production load'),
        (lambda a, h, r, ctx: a > 0.55 or h < 65, 'WARNING', 'Monitor trend — slight anomaly detected'),
        (lambda a, h, r, ctx: True, 'NORMAL', 'Continue routine monitoring'),  # Default
    ]

    # ─── Alert Tier Mapping ───────────────────────────────────────────────────
    # Determines which notification channels are triggered for a given severity.
    #
    #   none          → Dashboard display only, no notifications
    #   dashboard_only→ Dashboard display only (same as none, explicit)
    #   email         → Dashboard + Email
    #   full          → Dashboard + Email + WhatsApp + Auto Work Order
    _ALERT_TIER_MAP = {
        'NORMAL':       'none',
        'WARNING':      'dashboard_only',
        'HIGH_WARNING': 'email',
        'CRITICAL':     'full',
    }

    # ─────────────────────────────────────────────────────────────────────────

    def decide(self, motor, anomaly_score: float, fault_type: str,
               rul_days: float, health_score: float, context: dict, sequence: np.ndarray) -> dict:
        """
        Evaluates severity and determines recommendations based on model metrics,
        operational context, multi-signal consensus, persistence history, and
        false alarm suppression to produce a fully structured alert decision.
        """
        # Set default context
        if not context:
            context = {'shift': 'morning', 'load_level': 'normal'}

        severity = 'NORMAL'
        recommendation = 'Continue routine monitoring'

        # ── STEP 1: Rule Validation ──────────────────────────────────────────
        # Evaluate standard rules sequentially to get initial severity
        for condition, sev, rec in self.SEVERITY_RULES:
            if condition(anomaly_score, health_score, rul_days, context):
                severity = sev
                recommendation = rec
                break

        # Calculate primary cause using Z-score contribution analysis
        top_cause, max_idx, feature_desc = self._get_contribution_explanation_info(sequence)

        # Contextual inputs from scheduler
        load_level = context.get('load_level', 'normal')
        recently_maintained = context.get('recently_maintained', False)
        long_running = context.get('long_running', False)

        sensor_malfunction = context.get('sensor_malfunction', False)
        sensor_malfunction_reason = context.get('sensor_malfunction_reason', '')
        ambient_shift = context.get('ambient_shift', False)
        in_transient_phase = context.get('in_transient_phase', False)
        in_shift_handover = context.get('in_shift_handover', False)

        has_rising_trend = False
        elevated_count = 1 if anomaly_score > 0.8 else 0
        window_len = 1
        persistent_count = 0

        # ── STEP 2 & 5: Context Validation + False Alarm Suppression ─────────
        if sequence is not None and len(sequence) > 0:
            # Trend Analysis: check if the primary feature is in a rising trend
            feat_history = sequence[:, max_idx]
            first_half_avg = np.mean(feat_history[:5])
            last_half_avg = np.mean(feat_history[-5:])
            has_rising_trend = (last_half_avg - first_half_avg) > 0.3

            # Persistence History: Query recent severity/anomaly history from DB
            history_query = text("""
                SELECT severity, anomaly_score FROM prediction_results
                WHERE motor_id = :mid
                ORDER BY predicted_at DESC
                LIMIT 4
            """)
            try:
                with self.engine.connect() as conn:
                    history = conn.execute(history_query, {"mid": motor.motor_id}).fetchall()
            except Exception as e:
                print(f"[DecisionEngine Warning] Could not fetch prediction history: {e}")
                history = []

            for row in history:
                prev_score = float(row[1]) if row[1] is not None else 0.0
                if prev_score > 0.8:
                    elevated_count += 1

            window_len = len(history) + 1
            is_transient = window_len >= 3 and elevated_count <= 1 and not has_rising_trend

            # ── Apply False Alarm Suppression Rules ──────────────────────────
            if not sensor_malfunction:
                # Scenario A: Post-Maintenance Bedding-in Phase
                if recently_maintained and anomaly_score <= 1.4:
                    severity = 'NORMAL'
                    recommendation = 'Continue routine monitoring'
                    top_cause = f"Variance in {feature_desc} is expected during post-maintenance stabilization phase."

                # Scenario B: High Production Load Natural Scaling
                elif load_level == 'high' and anomaly_score <= 1.3 and feature_desc in ['Average Temperature', 'Peak Temperature', 'Average Motor Current']:
                    severity = 'NORMAL'
                    recommendation = 'Continue routine monitoring'
                    top_cause = f"Elevated {feature_desc} is normal and expected under high production load."

                # Scenario C: Long-running Thermal Equilibrium
                elif long_running and feature_desc in ['Average Temperature', 'Peak Temperature'] and not has_rising_trend and anomaly_score <= 1.2:
                    severity = 'NORMAL'
                    recommendation = 'Continue routine monitoring'
                    top_cause = f"Steady-state thermal rise in {feature_desc} is expected for long-running uptime."

                # Scenario D: Room/Ambient Temperature Shift (HVAC Change)
                elif ambient_shift and feature_desc in ['Average Temperature', 'Peak Temperature']:
                    if self._SEVERITY_RANK.get(severity, 0) >= self._SEVERITY_RANK['CRITICAL']:
                        severity = 'HIGH_WARNING'
                        recommendation = 'Check room HVAC and ambient cooling'
                    else:
                        severity = 'NORMAL'
                        recommendation = 'Continue routine monitoring'
                    top_cause = f"Elevated {feature_desc} matches room-wide ambient temperature shift across all motors."

                # Scenario E: Transient Startup / Shutdown Phase
                elif in_transient_phase and feature_desc in ['Average Motor Current', 'Vibration RMS', 'Vibration Peak Acceleration']:
                    severity = 'NORMAL'
                    recommendation = 'Allow transient start-up/stop sequence to stabilize'
                    top_cause = f"Elevated {feature_desc} is expected during transient startup/stop state."

                # Scenario F: Shift Handover Calibration Window
                elif in_shift_handover and anomaly_score <= 1.4:
                    severity = 'NORMAL'
                    recommendation = 'Monitor shift handover period. Operational changes expected'
                    top_cause = f"Telemetry fluctuations in {feature_desc} are common during shift handover windows."

                # Scenario G: Raw transient spike (single-window anomaly, no trend)
                elif is_transient:
                    if self._SEVERITY_RANK.get(severity, 0) >= self._SEVERITY_RANK['CRITICAL']:
                        severity = 'HIGH_WARNING'
                        recommendation = 'Monitor closely — transient telemetry spike detected'
                    elif self._SEVERITY_RANK.get(severity, 0) >= self._SEVERITY_RANK['HIGH_WARNING']:
                        severity = 'WARNING'
                        recommendation = 'Monitor closely — transient telemetry spike detected'
                    else:
                        severity = 'NORMAL'
                        recommendation = 'Continue routine monitoring'
                    top_cause = f"Transient telemetry anomaly in {feature_desc} detected. Trend analysis shows no sustained degradation pattern yet."
                else:
                    # Confirmed degradation
                    trend_status = " Sustained degradation trend confirmed by temporal trend verification." if has_rising_trend else ""
                    top_cause = f"{top_cause}{trend_status}"

        # ── CRITICAL SANITY FILTER: Sensor Malfunction ───────────────────────
        if sensor_malfunction:
            severity = 'WARNING'
            recommendation = 'Check sensor wiring and connection immediately'
            top_cause = f"Sensor Fault: {sensor_malfunction_reason}. Flatline/Null reading detected, not a motor degradation state."

        # ── STEP 3: Multi-Signal Consensus Gate ──────────────────────────────
        # A severity upgrade requires ≥2 of 3 signals (anomaly, health, RUL)
        # to independently confirm the condition. This prevents single-signal
        # false alarms from triggering expensive notifications.
        consensus_votes, consensus_downgrade = self._multi_signal_consensus(
            anomaly_score, health_score, rul_days, severity
        )

        if consensus_downgrade:
            old_severity = severity
            severity = consensus_downgrade
            print(f"[DecisionEngine] [Consensus] Motor {motor.motor_id}: "
                  f"Only {consensus_votes}/3 signals agree. "
                  f"Downgraded {old_severity} → {severity}.")

        # ── STEP 4: Persistence Check ─────────────────────────────────────────
        # HIGH_WARNING and CRITICAL require anomaly to be sustained across
        # ≥3 consecutive windows (~15 minutes). A single elevated reading
        # is treated as transient and capped at WARNING.
        if self._SEVERITY_RANK.get(severity, 0) >= self._SEVERITY_RANK['HIGH_WARNING']:
            persistent_count = self._persistence_check(motor.motor_id, anomaly_score)
            if persistent_count < 3:
                old_severity = severity
                severity = 'WARNING'
                recommendation = 'Monitor closely — anomaly not yet sustained across 3 windows'
                print(f"[DecisionEngine] [Persistence] Motor {motor.motor_id}: "
                      f"Anomaly only in {persistent_count}/3 required windows. "
                      f"Capped {old_severity} → WARNING.")

        # ── STEP 6: Alert Tier Assignment ────────────────────────────────────
        alert_tier = self._assign_alert_tier(severity)

        # ── Build XAI Explanation Details ────────────────────────────────────
        exp_details = []

        # 1. Trend verification
        if sequence is not None and len(sequence) > 0:
            if has_rising_trend:
                exp_details.append(f"[Verifikasi Tren]: Rata-rata nilai {feature_desc} pada 5 langkah terakhir naik signifikan (Kenaikan > 0.3 StdDev).")
            else:
                exp_details.append(f"[Verifikasi Tren]: Nilai rata-rata {feature_desc} stabil dan tidak menunjukkan grafik kenaikan berlanjut.")

        # 2. Multi-Signal Consensus result
        exp_details.append(
            f"[Konsensus Multi-Sinyal]: {consensus_votes} dari 3 sinyal model (Anomaly Score, Health Score, RUL) "
            f"melewati ambang batas status ini. "
            f"{'Konsensus terpenuhi.' if consensus_votes >= 2 else 'Konsensus tidak terpenuhi — alarm di-downgrade.'}"
        )

        # 3. Persistence check result
        exp_details.append(
            f"[Persistensi Alarm]: Anomaly score terdeteksi pada {persistent_count} dari minimal 3 window berturut-turut "
            f"yang dibutuhkan untuk konfirmasi {'HIGH_WARNING/CRITICAL' if self._SEVERITY_RANK.get(severity, 0) >= 2 else 'status saat ini'}."
        )

        # 4. Persistence density (historical)
        exp_details.append(f"[Kerapatan Alarm]: Terdeteksi {elevated_count} langkah anomali dari {window_len} jendela pengamatan terakhir.")

        # 5. Ambient temperature shift
        if ambient_shift:
            exp_details.append("[Suhu Lingkungan]: Seluruh motor aktif mengalami kenaikan suhu bersamaan (Indikasi masalah HVAC ruangan).")
        else:
            exp_details.append("[Suhu Lingkungan]: Suhu motor lain normal, memvalidasi anomali terlokalisir pada bearing mesin ini.")

        # 6. Transient Startup/Stop Phase
        if in_transient_phase:
            exp_details.append("[Fase Transisi]: Kecepatan putar (RPM) berubah tajam, menunjukkan siklus Start-Up atau Shut-Down sedang berlangsung.")
        else:
            exp_details.append("[Fase Transisi]: Kecepatan putar motor stabil dalam mode operasional berjalan.")

        # 7. Maintenance window
        if recently_maintained:
            exp_details.append("[Status Pemeliharaan]: Mesin baru selesai dimaintenance dalam 24 jam terakhir (Fase adaptasi awal berjalan).")
        else:
            exp_details.append("[Status Pemeliharaan]: Tidak ada perintah kerja diselesaikan untuk aset ini dalam 24 jam terakhir.")

        # 8. Load level
        exp_details.append(f"[Kapasitas Beban]: Status pembebanan produksi pabrik saat ini adalah '{load_level.upper()}'.")

        # 9. Shift handover window
        if in_shift_handover:
            exp_details.append("[Jendela Operasional]: Telemetri diambil di sekitar jam pergantian regu operator (07:00 / 15:00 / 23:00).")
        else:
            exp_details.append("[Jendela Operasional]: Waktu telemetri berada di luar jendela pergantian regu operator.")

        # 10. Alert tier assigned
        tier_labels = {
            'none': 'Tidak ada notifikasi dikirim',
            'dashboard_only': 'Ditampilkan di dashboard saja',
            'email': 'Dashboard + Email notifikasi',
            'full': 'Dashboard + Email + WhatsApp + Work Order otomatis',
        }
        exp_details.append(f"[Tier Notifikasi]: Alert tier '{alert_tier}' ditetapkan — {tier_labels.get(alert_tier, alert_tier)}.")

        # Combine explanation details with newlines
        formatted_details = "\n".join([f"- {d}" for d in exp_details])
        full_top_cause = f"{top_cause}\n{formatted_details}"

        return {
            'motor_id': motor.motor_id,
            'predicted_at': datetime.now(),
            'health_score': float(health_score),
            'anomaly_score': float(anomaly_score),
            'fault_type': 'sensor_error' if sensor_malfunction else (fault_type if fault_type else 'healthy'),
            'rul_days': float(rul_days),
            'severity': severity,
            'recommendation': recommendation,
            'top_cause': full_top_cause,
            'alert_sent': False,
            # New fields for Alert Management
            'consensus_votes': int(consensus_votes),
            'alert_tier': alert_tier,
        }

    # ─── Layer 3: Multi-Signal Consensus Gate ────────────────────────────────

    def _multi_signal_consensus(self, anomaly_score: float, health_score: float,
                                 rul_days: float, current_severity: str):
        """
        Checks whether ≥2 of 3 model signals (anomaly_score, health_score, rul_days)
        independently agree with the proposed severity level. If fewer than 2 signals
        agree, the severity is downgraded by one level.

        Returns:
            (votes: int, downgraded_severity: str | None)
            downgraded_severity is None if no downgrade is needed.
        """
        current_rank = self._SEVERITY_RANK.get(current_severity, 0)

        # We only apply consensus gating to WARNING and above
        if current_rank < self._SEVERITY_RANK['WARNING']:
            return 0, None

        # Count how many signals exceed the threshold for the current severity level
        thresholds = self._CONSENSUS_THRESHOLDS.get(current_severity,
                     self._CONSENSUS_THRESHOLDS.get('WARNING'))

        a_thresh, h_thresh, r_thresh = thresholds
        votes = 0
        if anomaly_score >= a_thresh:
            votes += 1
        if health_score <= h_thresh:
            votes += 1
        if rul_days <= r_thresh:
            votes += 1

        # Require at least 2 of 3 signals to confirm the current severity
        if votes < 2:
            # Downgrade by one level
            severity_levels = ['NORMAL', 'WARNING', 'HIGH_WARNING', 'CRITICAL']
            downgraded_idx = max(0, current_rank - 1)
            return votes, severity_levels[downgraded_idx]

        return votes, None

    # ─── Layer 4: Persistence Check ──────────────────────────────────────────

    def _persistence_check(self, motor_id: str, current_score: float) -> int:
        """
        Queries the last 5 prediction_results rows for this motor and counts
        how many of the most recent consecutive windows (including current)
        had anomaly_score > 0.5.

        Returns:
            persistent_count (int) — number of consecutive elevated windows
                                     in the most recent run (including current).
        """
        # Current window always counts
        count = 1 if current_score > 0.5 else 0

        history_query = text("""
            SELECT anomaly_score FROM prediction_results
            WHERE motor_id = :mid
            ORDER BY predicted_at DESC
            LIMIT 5
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(history_query, {"mid": motor_id}).fetchall()
        except Exception as e:
            print(f"[DecisionEngine Warning] Persistence check DB error: {e}")
            return count

        # Walk backwards through history; stop at the first non-elevated window
        for row in rows:
            prev_score = float(row[0]) if row[0] is not None else 0.0
            if prev_score > 0.5:
                count += 1
            else:
                break  # Gap in persistence — streak broken

        return count

    # ─── Layer 6: Alert Tier Assignment ──────────────────────────────────────

    def _assign_alert_tier(self, severity: str) -> str:
        """
        Maps a severity level to its corresponding notification tier.

        Tier     | Dashboard | Email | WhatsApp | Work Order
        ---------|-----------|-------|----------|------------
        none     |    ✅     |  ❌   |    ❌    |     ❌
        dash_only|    ✅     |  ❌   |    ❌    |     ❌
        email    |    ✅     |  ✅   |    ❌    |     ❌
        full     |    ✅     |  ✅   |    ✅    |     ✅
        """
        return self._ALERT_TIER_MAP.get(severity, 'none')

    # ─── Contribution Analysis Helper ────────────────────────────────────────

    def _get_contribution_explanation_info(self, sequence: np.ndarray):
        """
        Helper to return max index, feature name and standard message for contribution analysis.
        """
        if sequence is None or len(sequence) == 0:
            return "No telemetry sequence available.", 0, "Telemetry"

        last_step = sequence[-1, :]
        abs_dev = np.abs(last_step)
        max_idx = int(np.argmax(abs_dev))
        max_val = float(last_step[max_idx])
        feature_name = FEATURE_COLS[max_idx]

        readable_names = {
            'temp_mean': 'Average Temperature',
            'temp_max': 'Peak Temperature',
            'vib_rms': 'Vibration RMS',
            'vib_peak': 'Vibration Peak Acceleration',
            'vib_kurtosis': 'Vibration Kurtosis Pulse',
            'current_mean': 'Average Motor Current',
            'current_thd': 'Current Distortion Proxy',
            'rpm_mean': 'Average Rotation Speed',
            'rpm_drop_pct': 'RPM Slip Percentage',
            'torque_mean': 'Average Torque Load',
            'load_ratio': 'Current-to-Speed Load Ratio',
            'temp_per_load': 'Temperature-to-Load Ratio',
            'power_estimate': 'Estimated Motor Power',
        }

        feature_desc = readable_names.get(feature_name, feature_name.replace('_', ' ').title())

        if abs_dev[max_idx] < 1.0:
            return "All parameters are operating within nominal boundaries.", max_idx, feature_desc

        pct_contrib = int(abs_dev[max_idx] / (np.sum(abs_dev) + 1e-8) * 100)
        pct_contrib = max(15, min(85, pct_contrib))

        if max_val > 0:
            msg = f"{feature_desc} is abnormally high. This parameter contributes {pct_contrib}% to the anomaly."
        else:
            msg = f"{feature_desc} has dropped below normal parameters. This parameter contributes {pct_contrib}% to the anomaly."

        return msg, max_idx, feature_desc
