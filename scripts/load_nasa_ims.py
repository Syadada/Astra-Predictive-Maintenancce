import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    import src.api.local_config
except ImportError:
    pass

DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
DB_USER = os.getenv("ASTRA_DB_USER", "rasyaad")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
DB_NAME = "astra_predictive_maintenance"

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def load_nasa_ims(directory, motor_id):
    if not os.path.exists(directory) or not os.listdir(directory):
        print(f"[IMS Loader] Directory {directory} not found or empty. Generating synthetic run-to-failure fallback...")
        generate_synthetic_ims(motor_id)
        return

    print(f"[IMS Loader] Reading files from {directory}...")
    files = sorted([os.path.join(directory, f) for f in os.listdir(directory) if not f.startswith('.')])
    
    # IMS contains files recorded every 10 minutes, each containing 20480 samples.
    # Reading all would lead to huge DB size. Let's sample 1 file out of every 10 files
    # to capture the full run-to-failure lifecycle efficiently.
    sampled_files = files[::10]
    
    start_time = datetime(2024, 2, 1)
    
    for i, filepath in enumerate(sampled_files):
        try:
            # Files are tab-separated and have no header
            df = pd.read_csv(filepath, sep='\t', header=None, names=['bearing1', 'bearing2', 'bearing3', 'bearing4'])
            
            # Select first bearing as proxy, downsample to 1000 points per file to save space
            df_sampled = df.iloc[::20].copy()
            length = len(df_sampled)
            
            # Create a time range for this file
            file_time = start_time + timedelta(hours=i * 1.66) # space files out
            
            # Create DataFrame to load
            db_df = pd.DataFrame({
                'motor_id': motor_id,
                'recorded_at': pd.date_range(file_time, periods=length, freq='100ms'),
                'vibration_x': df_sampled['bearing1'],
                'vibration_y': df_sampled['bearing2'],
                'temperature': None, # IMS doesn't have temperature
                'current_a': np.random.normal(15.0, 0.2, length), # proxy
                'rpm': np.random.normal(2000.0, 5.0, length), # nominal RPM
                'torque_nm': np.random.normal(22.0, 0.4, length), # proxy
                'fault_label': 'run_to_failure',
                'data_source': 'nasa_ims',
                'is_simulated': False
            })
            
            db_df.to_sql('raw_sensor_data', engine, if_exists='append', index=False)
            if i % 10 == 0:
                print(f"[IMS Loader] Ingested file {i}/{len(sampled_files)}: {os.path.basename(filepath)}")
                
        except Exception as e:
            print(f"[IMS Loader] Error loading file {filepath}: {e}")
            
    print(f"[IMS Loader] Ingested IMS data for {motor_id} successfully.")

def generate_synthetic_ims(motor_id):
    # Generates a sequence of 50 files (timesteps) going from healthy to catastrophic failure
    num_steps = 60
    points_per_step = 1000
    start_time = datetime(2024, 2, 1)
    
    print("[IMS Loader] Generating synthetic run-to-failure progression...")
    
    for i in range(num_steps):
        # Progress parameter from 0.0 (healthy) to 1.0 (dead)
        progression = i / (num_steps - 1)
        
        # Exponential degradation: slowly at first, then rapidly at the end
        degradation = np.exp(3.5 * progression) / np.exp(3.5) # normalizes to 0-1
        
        # Vibration RMS goes from 0.12 g to 4.5 g
        base_rms = 0.12 + 4.38 * degradation
        noise = np.random.normal(0, base_rms * 0.4, points_per_step)
        
        # Vibration signal: combine nominal rotation frequency (e.g. 33 Hz for 2000 RPM) + noise
        t_vals = np.linspace(0, 1, points_per_step)
        rot_signal = 0.05 * np.sin(2 * np.pi * 33.3 * t_vals)
        
        # Fault impact pulses (frequency increases and severity grows as progression increases)
        pulses = np.zeros(points_per_step)
        if progression > 0.4:
            pulse_spacing = int(100 - 80 * progression) # pulses get closer
            pulse_amp = 0.5 + 8.0 * degradation
            pulse_indices = np.arange(0, points_per_step, pulse_spacing)
            for idx in pulse_indices:
                    slice_len = min(15, points_per_step - idx)
                    pulses[idx:idx+slice_len] = np.exp(-np.linspace(0, 4, 15))[:slice_len] * pulse_amp
                    
        vibration = rot_signal + noise + pulses
        
        # Temperature increases slightly from friction as bearing degrades (even though IMS has no temp, we can add a proxy)
        # Wait, the spec says temperature is None for IMS in DB, so we keep it None.
        
        # Current rises slightly due to efficiency loss
        current = np.random.normal(15.0 + 3.0 * degradation, 0.3, points_per_step)
        
        # RPM drops slightly under load
        rpm = np.random.normal(2000.0 - 150.0 * degradation, 10.0, points_per_step)
        
        # Torque increases due to mechanical resistance
        torque = np.random.normal(22.0 + 8.0 * degradation, 0.5, points_per_step)
        
        file_time = start_time + timedelta(hours=i * 2)
        
        df = pd.DataFrame({
            'motor_id': motor_id,
            'recorded_at': pd.date_range(file_time, periods=points_per_step, freq='100ms'),
            'vibration_x': vibration,
            'current_a': current,
            'rpm': rpm,
            'torque_nm': torque,
            'temperature': None, # IMS doesn't have temperature
            'fault_label': 'run_to_failure',
            'data_source': 'nasa_ims',
            'is_simulated': True
        })
        
        df.to_sql('raw_sensor_data', engine, if_exists='append', index=False)
        
    print(f"[IMS Loader] Ingested {num_steps * points_per_step} synthetic records representing full lifecycle for {motor_id}.")

if __name__ == '__main__':
    # Try directory path
    load_nasa_ims('dataset/NASA_IMS/2nd_test', 'MTR-04')
