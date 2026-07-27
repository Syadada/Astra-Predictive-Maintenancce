import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from collections import namedtuple

# Add root folder to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.pipeline.cleaning import CleaningPipeline
from src.pipeline.features import FeatureEngineeringPipeline

DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
DB_NAME = "astra_predictive_maintenance"

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def run_bulk_pipeline():
    print("[Bulk Pipeline] Connecting to database...")
    cleaner = CleaningPipeline()
    engineer = FeatureEngineeringPipeline()
    
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE feature_windows CASCADE"))
        conn.commit()
    print("[Bulk Pipeline] Cleared feature_windows table.")
    
    # Query motors
    motors_df = pd.read_sql("SELECT * FROM motors", engine)
    print(f"[Bulk Pipeline] Found {len(motors_df)} motors to process.")
    
    # Simple Mock Motor namedtuple
    Motor = namedtuple('Motor', ['motor_id', 'nominal_rpm', 'nominal_current'])
    
    for _, motor_row in motors_df.iterrows():
        motor = Motor(
            motor_id=motor_row['motor_id'],
            nominal_rpm=motor_row['nominal_rpm'],
            nominal_current=motor_row['nominal_current']
        )
        print(f"\n[Bulk Pipeline] Processing motor {motor.motor_id}...")
        
        # Query raw data
        raw_df = pd.read_sql(f"SELECT * FROM raw_sensor_data WHERE motor_id = '{motor.motor_id}' ORDER BY recorded_at ASC", engine)
        if len(raw_df) == 0:
            print(f"[Bulk Pipeline] No raw data found for {motor.motor_id}. Skipping.")
            continue
            
        print(f"[Bulk Pipeline] Loaded {len(raw_df)} raw records. Running window segmentation...")
        
        # Segment into 30-second windows.
        # Since recorded_at is datetime, we can resample or group by 30-second intervals
        raw_df['recorded_at'] = pd.to_datetime(raw_df['recorded_at'])
        raw_df = raw_df.set_index('recorded_at')
        
        # Group by 30s intervals
        grouper = raw_df.groupby(pd.Grouper(freq='30s'))
        
        feature_records = []
        
        # Get production context shift / load level
        # For simplicity, we can default these or query the database
        shift = 'morning'
        load_level = 'normal'
        
        # Iterate over groups
        count = 0
        for timestamp, group in grouper:
            if len(group) < 1:  # Need at least 1 point
                continue
                
            group_reset = group.reset_index()
            # Clean
            cleaned_group = cleaner.clean(group_reset, motor)
            
            # Engineer features
            try:
                features = engineer.engineer(cleaned_group, motor)
                
                # Add context metadata
                features['shift'] = shift
                features['load_level'] = load_level
                
                feature_records.append(features)
                count += 1
            except Exception as e:
                print(f"Error on window {timestamp}: {e}")
                
            if count % 100 == 0 and count > 0:
                print(f"[Bulk Pipeline] Processed {count} windows...")
        
        if feature_records:
            feat_df = pd.DataFrame(feature_records)
            # Remove any unwanted columns not in database schema
            cols_to_drop = [c for c in feat_df.columns if c not in [
                'motor_id', 'window_start', 'window_end', 'temp_mean', 'temp_max', 'temp_min', 'temp_slope', 'temp_std',
                'vib_rms', 'vib_peak', 'vib_kurtosis', 'vib_skewness', 'vib_crest', 'vib_fft_low', 'vib_fft_high',
                'current_mean', 'current_std', 'current_thd', 'current_slope', 'rpm_mean', 'rpm_std', 'rpm_drop_pct',
                'torque_mean', 'torque_std', 'torque_peak', 'load_ratio', 'temp_per_load', 'power_estimate',
                'temp_null_pct', 'vib_null_pct', 'has_sensor_error', 'shift', 'load_level', 'created_at'
            ]]
            feat_df = feat_df.drop(columns=cols_to_drop, errors='ignore')
            
            # Save to PostgreSQL
            feat_df.to_sql('feature_windows', engine, if_exists='append', index=False)
            print(f"[Bulk Pipeline] Ingested {len(feat_df)} feature windows for {motor.motor_id}.")
            
if __name__ == '__main__':
    run_bulk_pipeline()
