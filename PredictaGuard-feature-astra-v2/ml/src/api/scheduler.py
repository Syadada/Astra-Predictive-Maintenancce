import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from collections import namedtuple
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
        context = {'shift': 'morning', 'load_level': 'normal', 'ambient_temp': 25.0}
        with engine.connect() as conn:
            res_ctx = conn.execute(text("SELECT shift, load_level, ambient_temp FROM production_context ORDER BY id DESC LIMIT 1")).fetchone()
            if res_ctx:
                context['shift'] = res_ctx[0]
                context['load_level'] = res_ctx[1]
                context['ambient_temp'] = res_ctx[2] if res_ctx[2] is not None else 25.0
                
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

            # Extract latest window to compute context-aware metrics
            latest_window = windows_df.iloc[-1]

            # 1. Sensor Malfunction
            sensor_malfunction = False
            sensor_malfunction_reason = ""
            has_error = latest_window.get('has_sensor_error', False)
            if pd.notna(has_error) and bool(has_error):
                sensor_malfunction = True
                sensor_malfunction_reason = "High percentage of missing telemetry (sensor error flagged)"
            else:
                if len(windows_df) >= 5:
                    last_5_temps = windows_df['temp_mean'].iloc[-5:].dropna().tolist()
                    if len(last_5_temps) == 5 and all(t == last_5_temps[0] for t in last_5_temps):
                        sensor_malfunction = True
                        sensor_malfunction_reason = f"Temperature sensor flatline detected at {last_5_temps[0]}°C"
                        
                    last_5_vibs = windows_df['vib_rms'].iloc[-5:].dropna().tolist()
                    if len(last_5_vibs) == 5 and all(v == last_5_vibs[0] for v in last_5_vibs):
                        sensor_malfunction = True
                        sensor_malfunction_reason = f"Vibration sensor flatline detected at {last_5_vibs[0]} mm/s"
            
            motor_context['sensor_malfunction'] = sensor_malfunction
            motor_context['sensor_malfunction_reason'] = sensor_malfunction_reason

            # 2. Ambient Shift
            ambient_shift = False
            if context.get('ambient_temp', 25.0) > 30.0:
                ambient_shift = True
            motor_context['ambient_shift'] = ambient_shift

            # 3. Transient Phase
            in_transient_phase = False
            if 'rpm_std' in latest_window and latest_window['rpm_std'] is not None and pd.notna(latest_window['rpm_std']) and latest_window['rpm_std'] > 50.0:
                in_transient_phase = True
            elif len(windows_df) >= 2:
                prev_rpm = windows_df['rpm_mean'].iloc[-2]
                curr_rpm = windows_df['rpm_mean'].iloc[-1]
                if pd.notna(prev_rpm) and pd.notna(curr_rpm) and abs(curr_rpm - prev_rpm) > 150.0:
                    in_transient_phase = True
            motor_context['in_transient_phase'] = in_transient_phase

            # 4. Shift Handover
            in_shift_handover = False
            if 'window_end' in latest_window and latest_window['window_end'] is not None and pd.notna(latest_window['window_end']):
                latest_time = pd.to_datetime(latest_window['window_end'])
                for handover_hour in [7, 15, 23]:
                    handover_dt = latest_time.replace(hour=handover_hour, minute=0, second=0, microsecond=0)
                    time_diff = abs((latest_time - handover_dt).total_seconds())
                    if time_diff <= 900: # 15 minutes
                        in_shift_handover = True
                        break
            motor_context['in_shift_handover'] = in_shift_handover
            
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
            
            # Insert into database
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO prediction_results (
                            motor_id, predicted_at, health_score, anomaly_score, fault_type, 
                            rul_days, severity, recommendation, top_cause, alert_sent
                        ) VALUES (
                            :mid, :pat, :hs, :as_, :ft, :rul, :sev, :rec, :cause, :alert
                        )
                    """),
                    {
                        "mid": decision['motor_id'],
                        "pat": decision['predicted_at'],
                        "hs": decision['health_score'],
                        "as_": decision['anomaly_score'],
                        "ft": decision['fault_type'],
                        "rul": decision['rul_days'],
                        "sev": decision['severity'],
                        "rec": decision['recommendation'],
                        "cause": decision['top_cause'],
                        "alert": decision['alert_sent']
                    }
                )
                conn.commit()
                
            # Dispatch warning/critical alerts
            if decision['severity'] in ['WARNING', 'CRITICAL']:
                print(f"[Scheduler] Dispatching alerts for {motor.motor_id} due to {decision['severity']} status...")
                sent = notification_service.send(motor, decision)
                if sent:
                    # Update database to mark alert_sent = True
                    with engine.connect() as conn:
                        conn.execute(
                            text("UPDATE prediction_results SET alert_sent = TRUE WHERE motor_id = :mid AND predicted_at = :pat"),
                            {"mid": decision['motor_id'], "pat": decision['predicted_at']}
                        )
                        conn.commit()
                        
            print(f"[Scheduler] Completed inference for motor {motor.motor_id} | Health: {decision['health_score']:.1f}% | Severity: {decision['severity']}")
            
    except Exception as e:
        print(f"[Scheduler Error] Inference exception: {e}")

# Register jobs
scheduler.add_job(run_feature_pipeline, 'interval', seconds=30, id='feature_pipeline')
scheduler.add_job(run_inference, 'interval', minutes=5, id='inference_pipeline')
