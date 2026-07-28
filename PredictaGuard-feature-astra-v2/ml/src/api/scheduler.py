import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from collections import namedtuple
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Alert cooldown settings
# HIGH_WARNING: email is suppressed if already sent within this window
_EMAIL_COOLDOWN_HOURS = 2
# Tracks previous severity per motor to detect status transitions (in-memory cache)
_motor_previous_severity: dict = {}

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.cleaning import CleaningPipeline
from src.pipeline.features import FeatureEngineeringPipeline
from src.pipeline.sequence import SequenceBuilder
from src.api.inference import InferenceOrchestrator
from src.decision.engine import DecisionEngine
from src.api.notifications import NotificationService

DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
DB_NAME = "astra_predictive_maintenance"

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
scheduler = AsyncIOScheduler()

# Initialize processors
cleaning_pipeline = CleaningPipeline()
feature_pipeline = FeatureEngineeringPipeline()
sequence_builder = SequenceBuilder(scaler_dir='models')
inference_orchestrator = InferenceOrchestrator(models_dir='models')
decision_engine = DecisionEngine(scaler_dir='models')
notification_service = NotificationService()

Motor = namedtuple('Motor', ['motor_id', 'name', 'location', 'nominal_rpm', 'nominal_current'])

def get_motors():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT motor_id, name, location, nominal_rpm, nominal_current FROM motors"))
        return [Motor(*row) for row in res.fetchall()]

def get_last_processed_time(motor_id):
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT MAX(window_end) FROM feature_windows WHERE motor_id = :mid"),
            {"mid": motor_id}
        ).fetchone()
        return res[0] if res and res[0] else None

async def run_feature_pipeline():
    """
    JOB 1: Pipeline cleaning + feature engineering
    Runs every 30 seconds to process unprocessed raw telemetry.
    """
    print("[Scheduler] Running background feature extraction pipeline...")
    try:
        motors = get_motors()
        for motor in motors:
            last_processed = get_last_processed_time(motor.motor_id)
            
            # Fetch raw data after last processed time
            if last_processed:
                query = text("""
                    SELECT * FROM raw_sensor_data
                    WHERE motor_id = :mid AND recorded_at > :last_p
                    ORDER BY recorded_at ASC
                """)
                params = {"mid": motor.motor_id, "last_p": last_processed}
            else:
                # Start from the earliest raw record if nothing has been processed
                query = text("""
                    SELECT * FROM raw_sensor_data
                    WHERE motor_id = :mid
                    ORDER BY recorded_at ASC
                    LIMIT 2000
                """)
                params = {"mid": motor.motor_id}
                
            raw_df = pd.read_sql(query, engine, params=params)
            if len(raw_df) == 0:
                continue
                
            # Convert to datetime and sort
            raw_df['recorded_at'] = pd.to_datetime(raw_df['recorded_at'])
            raw_df = raw_df.sort_values('recorded_at')
            
            # Group raw data into 30-second windows
            # Align time boundaries
            start_time = raw_df['recorded_at'].min()
            end_time = raw_df['recorded_at'].max()
            
            current_start = start_time
            feature_records = []
            
            while current_start + timedelta(seconds=30) <= end_time:
                current_end = current_start + timedelta(seconds=30)
                window_mask = (raw_df['recorded_at'] >= current_start) & (raw_df['recorded_at'] < current_end)
                window_df = raw_df[window_mask].reset_index(drop=True)
                
                if len(window_df) >= 1: # Process if we have data
                    cleaned = cleaning_pipeline.clean(window_df, motor)
                    features = feature_pipeline.engineer(cleaned, motor)
                    
                    # Seeding shift context
                    hour = current_end.hour
                    if 6 <= hour < 14:
                        features['shift'] = 'morning'
                    elif 14 <= hour < 22:
                        features['shift'] = 'afternoon'
                    else:
                        features['shift'] = 'night'
                        
                    features['load_level'] = 'normal' # Default
                    feature_records.append(features)
                    
                current_start = current_end
                
            if feature_records:
                feat_df = pd.DataFrame(feature_records)
                # Drop columns not in feature_windows table schema
                cols_to_keep = [
                    'motor_id', 'window_start', 'window_end', 'temp_mean', 'temp_max', 'temp_min', 'temp_slope', 'temp_std',
                    'vib_rms', 'vib_peak', 'vib_kurtosis', 'vib_skewness', 'vib_crest', 'vib_fft_low', 'vib_fft_high',
                    'current_mean', 'current_std', 'current_thd', 'current_slope', 'rpm_mean', 'rpm_std', 'rpm_drop_pct',
                    'torque_mean', 'torque_std', 'torque_peak', 'load_ratio', 'temp_per_load', 'power_estimate',
                    'temp_null_pct', 'vib_null_pct', 'has_sensor_error', 'shift', 'load_level'
                ]
                cols_to_drop = [c for c in feat_df.columns if c not in cols_to_keep]
                feat_df = feat_df.drop(columns=cols_to_drop, errors='ignore')
                
                feat_df.to_sql('feature_windows', engine, if_exists='append', index=False)
                print(f"[Scheduler] Ingested {len(feat_df)} new windows for motor {motor.motor_id}")
                
    except Exception as e:
        print(f"[Scheduler Error] Feature pipeline exception: {e}")

async def run_inference():
    """
    JOB 2: Model inference + decision engine
    Runs every 5 minutes.
    For testing/simulation, we can run it concurrently or call it.
    """
    print("[Scheduler] Running background model inference and decision pipeline...")
    try:
        motors = get_motors()
        
        # Load production context
        context = {'shift': 'morning', 'load_level': 'normal'}
        with engine.connect() as conn:
            res_ctx = conn.execute(text("SELECT shift, load_level FROM production_context ORDER BY id DESC LIMIT 1")).fetchone()
            if res_ctx:
                context['shift'] = res_ctx[0]
                context['load_level'] = res_ctx[1]
                
        for motor in motors:
            # Create a copy of the base production context to enrich with motor-specific metrics
            motor_context = context.copy()
            
            # Query last 120 feature windows (ascending order)
            query = text("""
                SELECT * FROM (
                    SELECT * FROM feature_windows
                    WHERE motor_id = :mid
                    ORDER BY window_end DESC
                    LIMIT 120
                ) sub ORDER BY window_end ASC
            """)
            windows_df = pd.read_sql(query, engine, params={"mid": motor.motor_id})
            
            if len(windows_df) < 20:
                print(f"[Scheduler] Motor {motor.motor_id} has insufficient windows ({len(windows_df)}/20). Skipping inference.")
                continue
                
            # Check if the motor was recently maintained (work order completed in the last 24 hours)
            recently_maintained = False
            try:
                with engine.connect() as conn:
                    res_wo = conn.execute(text("""
                        SELECT created_at FROM work_orders 
                        WHERE asset_id = :mid AND status = 'Completed' 
                        ORDER BY created_at DESC LIMIT 1
                    """), {"mid": motor.motor_id}).fetchone()
                    if res_wo:
                        delta = datetime.now() - res_wo[0].replace(tzinfo=None)
                        if delta.total_seconds() < 86400:
                            recently_maintained = True
            except Exception as e:
                print(f"[Scheduler Warning] Failed to check recent work orders: {e}")
            motor_context['recently_maintained'] = recently_maintained
            
            # Check if the motor has been running continuously (RPM > 100 in the last 12 feature windows = 1 hour)
            long_running = False
            if 'rpm_mean' in windows_df.columns:
                active_windows = (windows_df['rpm_mean'] > 100.0).sum()
                if active_windows >= 12:
                    long_running = True
            motor_context['long_running'] = long_running
            
            # Build sequence
            sequence = sequence_builder.build_sequence(windows_df, motor.motor_id)
            
            # Predict
            preds = inference_orchestrator.predict(sequence, motor.motor_id)
            
            # Decide
            decision = decision_engine.decide(
                motor=motor,
                anomaly_score=preds['anomaly_score'],
                fault_type=preds['fault_type'],
                rul_days=preds['rul_days'],
                health_score=preds['health_score'],
                context=motor_context,
                sequence=sequence
            )
            
            current_severity = decision['severity']
            alert_tier = decision.get('alert_tier', 'none')
            previous_severity = _motor_previous_severity.get(motor.motor_id, 'NORMAL')
            
            # ── Determine if notification should be sent ──────────────────
            should_notify, notify_reason = _should_send_notification(
                motor_id=motor.motor_id,
                current_severity=current_severity,
                alert_tier=alert_tier,
                previous_severity=previous_severity,
                db_engine=engine,
            )
            
            # Update in-memory previous severity tracker
            _motor_previous_severity[motor.motor_id] = current_severity

            # Insert into database (including new consensus_votes and alert_tier columns)
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO prediction_results (
                            motor_id, predicted_at, health_score, anomaly_score, fault_type,
                            rul_days, severity, recommendation, top_cause, alert_sent,
                            consensus_votes, alert_tier
                        ) VALUES (
                            :mid, :pat, :hs, :as_, :ft, :rul, :sev, :rec, :cause, :alert,
                            :cv, :tier
                        )
                    """),
                    {
                        "mid": decision['motor_id'],
                        "pat": decision['predicted_at'],
                        "hs": decision['health_score'],
                        "as_": decision['anomaly_score'],
                        "ft": decision['fault_type'],
                        "rul": decision['rul_days'],
                        "sev": current_severity,
                        "rec": decision['recommendation'],
                        "cause": decision['top_cause'],
                        "alert": False,
                        "cv": decision.get('consensus_votes', 0),
                        "tier": alert_tier,
                    }
                )
                conn.commit()

            # ── Tiered Notification Routing ───────────────────────────────
            if should_notify:
                print(f"[Scheduler] [{alert_tier.upper()}] Dispatching notification for "
                      f"{motor.motor_id} ({current_severity}) — {notify_reason}")
                sent = notification_service.send(motor, decision, alert_tier=alert_tier)
                if sent:
                    with engine.connect() as conn:
                        conn.execute(
                            text("UPDATE prediction_results SET alert_sent = TRUE "
                                 "WHERE motor_id = :mid AND predicted_at = :pat"),
                            {"mid": decision['motor_id'], "pat": decision['predicted_at']}
                        )
                        conn.commit()
            else:
                print(f"[Scheduler] Notification suppressed for {motor.motor_id} "
                      f"({current_severity}) — {notify_reason}")

            print(f"[Scheduler] Motor {motor.motor_id} | Health: {decision['health_score']:.1f}% "
                  f"| Severity: {current_severity} | Tier: {alert_tier} "
                  f"| Consensus: {decision.get('consensus_votes', 0)}/3")
            
    except Exception as e:
        print(f"[Scheduler Error] Inference exception: {e}")

# ─── Alert Management: Cooldown + Status Change Trigger ─────────────────────

_SEVERITY_RANK = {
    'NORMAL': 0,
    'WARNING': 1,
    'HIGH_WARNING': 2,
    'CRITICAL': 3,
}

def _should_send_notification(motor_id: str, current_severity: str, alert_tier: str,
                               previous_severity: str, db_engine) -> tuple:
    """
    Determines whether a notification should be sent based on:
    1. Alert tier (WARNING/dashboard_only → no external notification)
    2. Status change trigger (only notify on severity upgrades)
    3. Alert cooldown (HIGH_WARNING email has a 2-hour cooldown)
    4. CRITICAL always triggers a notification on any transition from non-CRITICAL

    Returns:
        (should_notify: bool, reason: str)
    """
    current_rank = _SEVERITY_RANK.get(current_severity, 0)
    previous_rank = _SEVERITY_RANK.get(previous_severity, 0)

    # Tier 'none' or 'dashboard_only': never send external notifications
    if alert_tier in ('none', 'dashboard_only'):
        return False, f"Tier '{alert_tier}' — dashboard display only, no external notification"

    # CRITICAL: always send if status upgraded from a lower level
    if current_severity == 'CRITICAL':
        if previous_severity != 'CRITICAL':
            return True, f"Status escalated from {previous_severity} → CRITICAL"
        else:
            # Already was CRITICAL; check if we re-entered (e.g., brief drop then back)
            # Still suppress repeated CRITICAL notifications without a status change
            return False, "Already in CRITICAL state — notification suppressed to prevent alert fatigue"

    # HIGH_WARNING (email tier): apply cooldown of _EMAIL_COOLDOWN_HOURS
    if current_severity == 'HIGH_WARNING':
        # Only send on upgrade (WARNING → HIGH_WARNING or NORMAL → HIGH_WARNING)
        if current_rank <= previous_rank:
            return False, f"No severity upgrade detected ({previous_severity} → {current_severity}) — email suppressed"

        # Check cooldown: was an email sent for this motor in the last N hours?
        cooldown_query = text("""
            SELECT MAX(predicted_at) FROM prediction_results
            WHERE motor_id = :mid
              AND alert_sent = TRUE
              AND severity = 'HIGH_WARNING'
        """)
        try:
            with db_engine.connect() as conn:
                last_sent = conn.execute(cooldown_query, {"mid": motor_id}).scalar()
        except Exception as e:
            print(f"[Scheduler Warning] Cooldown check failed: {e}")
            last_sent = None

        if last_sent is not None:
            last_sent = last_sent.replace(tzinfo=None)
            elapsed_hours = (datetime.now() - last_sent).total_seconds() / 3600
            if elapsed_hours < _EMAIL_COOLDOWN_HOURS:
                return False, (f"HIGH_WARNING email cooldown active "
                               f"(last sent {elapsed_hours:.1f}h ago, cooldown: {_EMAIL_COOLDOWN_HOURS}h)")

        return True, f"Status upgraded {previous_severity} → HIGH_WARNING"

    # Any other tier not handled above: suppress
    return False, f"Unhandled tier '{alert_tier}' — notification suppressed"


# Register jobs
scheduler.add_job(run_feature_pipeline, 'interval', seconds=30, id='feature_pipeline')
scheduler.add_job(run_inference, 'interval', minutes=5, id='inference_pipeline')
