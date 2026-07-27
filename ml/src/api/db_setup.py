import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime

# Inject local config directory to load credentials
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "5432"))
DB_USER = os.getenv("ASTRA_DB_USER", "postgres")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "")
DB_NAME = "astra_predictive_maintenance"

def create_database():
    print("[DB Setup] Connecting to 'postgres' database to verify/create target database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if target db exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cursor.fetchone()
    if not exists:
        print(f"[DB Setup] Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"[DB Setup] Database '{DB_NAME}' created successfully.")
    else:
        print(f"[DB Setup] Database '{DB_NAME}' already exists.")
        
    cursor.close()
    conn.close()

def create_tables():
    print(f"[DB Setup] Connecting to '{DB_NAME}' to initialize schemas...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # 1. motors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motors (
            motor_id        VARCHAR(10) PRIMARY KEY,  -- MTR-01 sd MTR-06
            name            VARCHAR(50),              -- Conveyor, Pump, dll
            location        VARCHAR(50),              -- Line 1, Utility, dll
            power_kw        FLOAT,                    -- kapasitas motor
            nominal_rpm     INTEGER,                  -- RPM normal operasi
            nominal_current FLOAT,                    -- Current normal (Ampere)
            max_temp        FLOAT,                    -- batas suhu aman
            max_vibration   FLOAT,                    -- batas vibration aman
            is_critical     BOOLEAN,                  -- apakah mesin kritis
            data_source     VARCHAR(20),              -- 'paderborn'/'nasa_ims'/'cmapss'
            installed_at    TIMESTAMP
        );
    """)
    
    # 2. raw_sensor_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sensor_data (
            id              BIGSERIAL PRIMARY KEY,
            motor_id        VARCHAR(10) REFERENCES motors(motor_id),
            recorded_at     TIMESTAMP NOT NULL,       -- timestamp dari dataset asli
            ingested_at     TIMESTAMP DEFAULT NOW(),  -- kapan data masuk DB
            temperature     FLOAT,                    -- °C, bisa NULL
            vibration_x     FLOAT,                    -- mm/s atau g
            vibration_y     FLOAT,                    -- mm/s atau g (jika ada)
            current_a       FLOAT,                    -- Ampere
            rpm             FLOAT,                    -- rotasi per menit
            torque_nm       FLOAT,                    -- Newton-meter
            voltage         FLOAT,                    -- Volt (jika ada)
            data_source     VARCHAR(20),              -- asal dataset
            fault_label     VARCHAR(30),              -- label dari dataset asli
            is_simulated    BOOLEAN DEFAULT TRUE      -- tandai ini data simulasi
        );
    """)
    
    # 3. production_context table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_context (
            id              SERIAL PRIMARY KEY,
            recorded_at     TIMESTAMP NOT NULL,
            shift           VARCHAR(10),   -- 'morning'/'afternoon'/'night'
            load_level      VARCHAR(10),   -- 'low'/'normal'/'high'
            line_running    BOOLEAN,
            ambient_temp    FLOAT
        );
    """)
    
    # 4. feature_windows table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feature_windows (
            id              BIGSERIAL PRIMARY KEY,
            motor_id        VARCHAR(10) REFERENCES motors(motor_id),
            window_start    TIMESTAMP NOT NULL,
            window_end      TIMESTAMP NOT NULL,   -- ini yang jadi acuan "30 detik"

            -- Temperature features
            temp_mean       FLOAT,
            temp_max        FLOAT,
            temp_min        FLOAT,
            temp_slope      FLOAT,    -- tren naik/turun per menit
            temp_std        FLOAT,

            -- Vibration features
            vib_rms         FLOAT,    -- Root Mean Square energi getaran
            vib_peak        FLOAT,    -- nilai tertinggi dalam window
            vib_kurtosis    FLOAT,    -- ketajaman lonjakan (bearing fault indicator)
            vib_skewness    FLOAT,    -- asimetri distribusi
            vib_crest       FLOAT,    -- peak / RMS ratio
            vib_fft_low     FLOAT,    -- FFT low frequency energy
            vib_fft_high    FLOAT,    -- FFT high frequency energy

            -- Current features
            current_mean    FLOAT,
            current_std     FLOAT,
            current_thd     FLOAT,    -- Total Harmonic Distortion proxy
            current_slope   FLOAT,

            -- RPM features
            rpm_mean        FLOAT,
            rpm_std         FLOAT,
            rpm_drop_pct    FLOAT,    -- % drop dari nominal RPM mesin

            -- Torque features
            torque_mean     FLOAT,
            torque_std      FLOAT,
            torque_peak     FLOAT,

            -- Cross-parameter features
            load_ratio      FLOAT,    -- current_mean / rpm_mean
            temp_per_load   FLOAT,    -- temp_mean / current_mean
            power_estimate  FLOAT,    -- rpm_mean * torque_mean

            -- Data quality flags
            temp_null_pct   FLOAT,    -- % data null dalam window ini
            vib_null_pct    FLOAT,
            has_sensor_error BOOLEAN, -- apakah ada nilai tidak masuk akal

            -- Context
            shift           VARCHAR(10),
            load_level      VARCHAR(10),
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # 5. users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email VARCHAR(255) PRIMARY KEY,
            password VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            clearance VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            avatar TEXT
        );
    """)

    # 6. work_orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id TEXT PRIMARY KEY,
            asset_id TEXT,
            asset_name TEXT,
            description TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_tech VARCHAR(100) DEFAULT 'Unassigned'
        );
    """)

    # 7. notification_settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            id SERIAL PRIMARY KEY,
            smtp_server TEXT,
            smtp_port INTEGER,
            sender_email TEXT,
            sender_password TEXT,
            recipient_email TEXT,
            twilio_account_sid TEXT,
            twilio_auth_token TEXT,
            twilio_whatsapp_from TEXT,
            recipient_whatsapp TEXT,
            whatsapp_provider TEXT DEFAULT 'twilio',
            waha_server_url TEXT DEFAULT 'http://localhost:3000'
        );
    """)
    cursor.execute("ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS whatsapp_provider TEXT DEFAULT 'twilio'")
    cursor.execute("ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS waha_server_url TEXT DEFAULT 'http://localhost:3000'")

    # 8. prediction_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_results (
            id              BIGSERIAL PRIMARY KEY,
            motor_id        VARCHAR(10) REFERENCES motors(motor_id),
            predicted_at    TIMESTAMP NOT NULL,
            health_score    FLOAT,
            anomaly_score   FLOAT,
            fault_type      VARCHAR(50),
            rul_days        FLOAT,
            severity        VARCHAR(20),
            recommendation  TEXT,
            top_cause       TEXT,
            alert_sent      BOOLEAN DEFAULT FALSE
        );
    """)

    conn.commit()
    print("[DB Setup] Schemas initialized successfully.")
    
    # Seed default data
    # 1. Motors
    cursor.execute("SELECT COUNT(*) FROM motors")
    if cursor.fetchone()[0] == 0:
        print("[DB Setup] Seeding master motors...")
        motors_data = [
            ("MTR-01", "Conveyor Drive", "Line 1", 11.0, 1500, 22.0, 85.0, 4.5, True, "paderborn", datetime(2023, 5, 10)),
            ("MTR-02", "Compressor", "Utility", 55.0, 2950, 98.0, 90.0, 6.0, True, "paderborn", datetime(2022, 10, 15)),
            ("MTR-03", "Fan/Blower", "Line 2", 18.5, 1450, 35.0, 80.0, 5.0, False, "paderborn", datetime(2024, 1, 12)),
            ("MTR-04", "Pump", "Utility", 30.0, 1480, 58.0, 85.0, 8.0, True, "nasa_ims", datetime(2023, 8, 20)),
            ("MTR-05", "Mixer", "Line 1", 45.0, 980, 88.0, 95.0, 7.0, True, "cmapss", datetime(2021, 4, 5)),
            ("MTR-06", "Spindle", "Line 3", 7.5, 3000, 15.0, 75.0, 3.5, False, "paderborn", datetime(2024, 3, 1))
        ]
        cursor.executemany("""
            INSERT INTO motors (motor_id, name, location, power_kw, nominal_rpm, nominal_current, max_temp, max_vibration, is_critical, data_source, installed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, motors_data)
        conn.commit()
        print("[DB Setup] Seeded 6 motors.")

    # 2. Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("[DB Setup] Seeding users...")
        users_data = [
            ("superadmin@ASTRA.com", "admin123", "Justin Bieber", "Super Admin", "Level 4", "Lead Engineer & Predictive Analytics Specialist", "https://lh3.googleusercontent.com/aida-public/AB6AXuAJB3nF963ZDZN5AzByGsqb2MxVyIvYYJZPDV3NOPF900ug_3y-d7MEHM9IcmdVDLg62EThO7ZZgtVfPH2qBLypFdU6CntX3pU3T1JaCfwVtgGdlrtJC5dzHHTfJxSNG-UN1NvfxKBe1DzYgQaD3aqaZg3Xxnt5j4CGxyaLfpyjHJO3tUUkGQIBvHZZAZPScXVH5c1S1afsZtZtXFKb6SEtVWsYVchjtnhJNUrqnmceziBRB5_XQGZV4hDOih0mFzLsvnv-I80nDtU"),
            ("rasyaad@ASTRA.com", "admin123", "Rasyaad P. REDIANTO", "Super Admin", "Level 4", "Lead Systems Architect & Operational Hub Manager", "https://lh3.googleusercontent.com/a/ACg8ocIS0G1jJt84nO4VvHspYqR64m3s8QjI1KjR2-i6mUuG0w=s96-c"),
            ("admin@ASTRA.com", "admin123", "Operational Manager", "Admin", "Level 3", "Plant Operations Coordinator", None),
            ("maint@ASTRA.com", "maint123", "Ronny Prasad", "Maintenance", "Level 2", "Lead Maintenance Specialist", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256&h=256"),
            ("operator@ASTRA.com", "op123", "Floor Operator", "Operator", "Level 1", "Field Systems Operator", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=256&h=256")
        ]
        cursor.executemany("""
            INSERT INTO users (email, password, name, role, clearance, title, avatar)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, users_data)
        conn.commit()
        print("[DB Setup] Seeded default users.")

    # 3. Notification settings
    cursor.execute("SELECT COUNT(*) FROM notification_settings")
    if cursor.fetchone()[0] == 0:
        print("[DB Setup] Seeding default notification settings...")
        cursor.execute("""
            INSERT INTO notification_settings (id, smtp_server, smtp_port, sender_email, sender_password, recipient_email, twilio_account_sid, twilio_auth_token, twilio_whatsapp_from, recipient_whatsapp, whatsapp_provider, waha_server_url)
            VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "smtp.gmail.com",
            587,
            "rasyaadputraredianto@gmail.com",
            "your-app-password",
            "rasyaadputraredianto@gmail.com",
            "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "token_placeholder",
            "+14155238886",
            "+628999999999",
            "twilio",
            "http://localhost:3000"
        ))
        conn.commit()
        print("[DB Setup] Seeded default notification settings.")

    # 4. Work orders
    cursor.execute("SELECT COUNT(*) FROM work_orders")
    if cursor.fetchone()[0] == 0:
        print("[DB Setup] Seeding default work orders...")
        cursor.executemany("""
            INSERT INTO work_orders (id, asset_id, asset_name, description, status, created_at, assigned_tech)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, [
            ("WO-8821", "MTR-01", "Motor MTR-01 (Conveyor Drive)", "Replace outer race bearing assembly", "Completed", datetime(2026, 7, 1, 10, 0), "J. Sutherland"),
            ("WO-8902", "MTR-04", "Motor MTR-04 (Pump)", "Lubricate gearbox bearing drive", "Completed", datetime(2026, 7, 5, 14, 30), "M. Rossi"),
            ("WO-8905", "MTR-05", "Motor MTR-05 (Mixer)", "Calibrate telemetry transmitter speed loop", "Completed", datetime(2026, 7, 9, 9, 15), "S. O'Brien")
        ])
        conn.commit()
        print("[DB Setup] Seeded default work orders.")

    # 5. Production context initial data
    cursor.execute("SELECT COUNT(*) FROM production_context")
    if cursor.fetchone()[0] == 0:
        print("[DB Setup] Seeding initial production context...")
        cursor.execute("""
            INSERT INTO production_context (recorded_at, shift, load_level, line_running, ambient_temp)
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), 'morning', 'normal', True, 28.5))
        conn.commit()
        print("[DB Setup] Seeded initial production context.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_database()
    create_tables()
    print("[DB Setup] Finished setup.")
