import os
import sys
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.sequence import FEATURE_COLS

class DecisionEngine:
    def __init__(self, scaler_dir='models'):
        self.scaler_dir = scaler_dir
        
        # Setup Postgres database connection for historical persistence check
        DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
        DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
        DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
        DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
        DB_NAME = "astra_predictive_maintenance"
        
        self.engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

    SEVERITY_RULES = [
        # (condition_fn, severity, recommendation)
        (lambda a, h, r, ctx: a > 0.85 and h < 30, 'CRITICAL', 'Inspect immediately — shutdown risk'),
        (lambda a, h, r, ctx: r < 3, 'CRITICAL', 'Schedule emergency maintenance'),
        (lambda a, h, r, ctx: (a > 0.65 and h < 55) or r < 7, 'WARNING', 'Plan maintenance this week'),
        (lambda a, h, r, ctx: a > 0.65 and ctx.get('load_level') == 'high', 'WARNING', 'Monitor closely — high production load'),
        (lambda a, h, r, ctx: True, 'NORMAL', 'Continue routine monitoring') # Default
    ]

    def decide(self, motor, anomaly_score: float, fault_type: str, 
               rul_days: float, health_score: float, context: dict, sequence: np.ndarray) -> dict:
        """
        Evaluates severity and determines recommendations based on model metrics, operational context,
        prediction persistence history, and advanced feature trends to filter out false alarms.
        """
        # Set default context
        if not context:
            context = {'shift': 'morning', 'load_level': 'normal'}
            
        severity = 'NORMAL'
        recommendation = 'Continue routine monitoring'
        
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

        # ─── FALSE ALARM & CONTEXT-AWARE FILTERING ───
        if sequence is not None and len(sequence) > 0:
            # 1. Trend Analysis: check if the primary feature is in a rising trend (last 5 steps vs first 5 steps)
            feat_history = sequence[:, max_idx]
            first_half_avg = np.mean(feat_history[:5])
            last_half_avg = np.mean(feat_history[-5:])
            has_rising_trend = (last_half_avg - first_half_avg) > 0.3
            
            # 2. Persistence Check: Query recent severity history from Postgres
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
            
            # ─── Apply Suppression / Moderation Rules ───
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
                    if severity == 'CRITICAL':
                        severity = 'WARNING'
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
                    
                # Scenario G: Raw transient spike
                elif is_transient:
                    if severity == 'CRITICAL':
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

        # ─── CRITICAL SANITY FILTER 1: Sensor Malfunction ───
        if sensor_malfunction:
            # Overrule machine fault rules to indicate a sensor error instead
            severity = 'WARNING'
            recommendation = 'Check sensor wiring and connection immediately'
            top_cause = f"Sensor Fault: {sensor_malfunction_reason}. Flatline/Null reading detected, not a motor degradation state."

        # Build structured step-by-step XAI explanation list
        exp_details = []
        
        # 1. Trend verification
        if sequence is not None and len(sequence) > 0:
            if has_rising_trend:
                exp_details.append(f"[Verifikasi Tren]: Rata-rata nilai {feature_desc} pada 5 langkah terakhir naik signifikan (Kenaikan > 0.3 StdDev).")
            else:
                exp_details.append(f"[Verifikasi Tren]: Nilai rata-rata {feature_desc} stabil dan tidak menunjukkan grafik kenaikan berlanjut.")
        
        # 2. Persistence density
        exp_details.append(f"[Kerapatan Alarm]: Terdeteksi {elevated_count} langkah anomali dari {window_len} jendela pengamatan terakhir.")
        
        # 3. Ambient temperature shift
        if ambient_shift:
            exp_details.append("[Suhu Lingkungan]: Seluruh motor aktif mengalami kenaikan suhu bersamaan (Indikasi masalah HVAC ruangan).")
        else:
            exp_details.append("[Suhu Lingkungan]: Suhu motor lain normal, memvalidasi anomali terlokalisir pada bearing mesin ini.")
            
        # 4. Transient Startup/Stop Phase
        if in_transient_phase:
            exp_details.append("[Fase Transisi]: Kecepatan putar (RPM) berubah tajam, menunjukkan siklus Start-Up atau Shut-Down sedang berlangsung.")
        else:
            exp_details.append("[Fase Transisi]: Kecepatan putar motor stabil dalam mode operasional berjalan.")
            
        # 5. Maintenance window
        if recently_maintained:
            exp_details.append("[Status Pemeliharaan]: Mesin baru selesai dimaintenance dalam 24 jam terakhir (Fase adaptasi awal berjalan).")
        else:
            exp_details.append("[Status Pemeliharaan]: Tidak ada perintah kerja diselesaikan untuk aset ini dalam 24 jam terakhir.")
            
        # 6. Load level
        exp_details.append(f"[Kapasitas Beban]: Status pembebanan produksi pabrik saat ini adalah '{load_level.upper()}'.")
        
        # 7. Shift handover window
        if in_shift_handover:
            exp_details.append("[Jendela Operasional]: Telemetri diambil di sekitar jam pergantian regu operator (07:00 / 15:00 / 23:00).")
        else:
            exp_details.append("[Jendela Operasional]: Waktu telemetri berada di luar jendela pergantian regu operator.")

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
            'alert_sent': False
        }

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
            'power_estimate': 'Estimated Motor Power'
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
