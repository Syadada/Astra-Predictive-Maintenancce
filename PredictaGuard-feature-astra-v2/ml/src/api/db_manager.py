import os
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime

class DBManager:
    def __init__(self, project_root: str):
        self.db_dir = os.path.join(project_root, "data")
        os.makedirs(self.db_dir, exist_ok=True)
        self.init_db()

    def get_connection(self):
        try:
            import src.api.local_config
        except ImportError:
            pass
        return psycopg2.connect(
            host=os.getenv("ASTRA_DB_HOST", "localhost"),
            port=int(os.getenv("ASTRA_DB_PORT", "5432")),
            database=os.getenv("ASTRA_DB_NAME", "astra_predictive_maintenance"),
            user=os.getenv("ASTRA_DB_USER", "rasyaad"),
            password=os.getenv("ASTRA_DB_PASSWORD", "Sellevolerei1")
        )

    def init_db(self):
        """Creates the telemetry and work_orders tables if they don't exist and seeds them if empty."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                vibration_rms REAL,
                motor_current REAL,
                temperature REAL,
                flow_rate REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id TEXT PRIMARY KEY,
                asset_id TEXT,
                asset_name TEXT,
                description TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_tech VARCHAR(100) DEFAULT 'Unassigned'
            )
        """)
        cursor.execute("ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS assigned_tech VARCHAR(100) DEFAULT 'Unassigned'")
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
                waha_server_url TEXT DEFAULT 'http://localhost:3000',
                email_enabled BOOLEAN DEFAULT TRUE
            )
        """)
        cursor.execute("ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS whatsapp_provider TEXT DEFAULT 'twilio'")
        cursor.execute("ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS waha_server_url TEXT DEFAULT 'http://localhost:3000'")
        cursor.execute("ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN DEFAULT TRUE")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                clearance VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                avatar TEXT
            )
        """)
        conn.commit()

        # Check if notification_settings table is empty
        cursor.execute("SELECT COUNT(*) FROM notification_settings")
        ns_count = cursor.fetchone()[0]
        if ns_count == 0:
            print("[DBManager] Notification settings table is empty. Seeding defaults...")
            cursor.execute("""
                INSERT INTO notification_settings (id, smtp_server, smtp_port, sender_email, sender_password, recipient_email, twilio_account_sid, twilio_auth_token, twilio_whatsapp_from, recipient_whatsapp, whatsapp_provider, waha_server_url, email_enabled)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                "smtp.gmail.com",
                587,
                "sender@example.com",
                "your-app-password",
                "recipient@example.com",
                "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "token_placeholder",
                "+14155238886",
                "+628999999999",
                "twilio",
                "http://localhost:3000",
                True
            ))
            conn.commit()

        # Check if users table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        if user_count == 0:
            print("[DBManager] Users table is empty. Seeding authorization profiles...")
            users_to_seed = [
                ("superadmin@ASTRA.com", "admin123", "Justin Bieber", "Super Admin", "Level 4", "Lead Engineer & Predictive Analytics Specialist", "https://lh3.googleusercontent.com/aida-public/AB6AXuAJB3nF963ZDZN5AzByGsqb2MxVyIvYYJZPDV3NOPF900ug_3y-d7MEHM9IcmdVDLg62EThO7ZZgtVfPH2qBLypFdU6CntX3pU3T1JaCfwVtgGdlrtJC5dzHHTfJxSNG-UN1NvfxKBe1DzYgQaD3aqaZg3Xxnt5j4CGxyaLfpyjHJO3tUUkGQIBvHZZAZPScXVH5c1S1afsZtZtXFKb6SEtVWsYVchjtnhJNUrqnmceziBRB5_XQGZV4hDOih0mFzLsvnv-I80nDtU"),
                ("rasyaad@ASTRA.com", "admin123", "Rasyaad P. REDIANTO", "Super Admin", "Level 4", "Lead Systems Architect & Operational Hub Manager", "https://lh3.googleusercontent.com/a/ACg8ocIS0G1jJt84nO4VvHspYqR64m3s8QjI1KjR2-i6mUuG0w=s96-c"),
                ("admin@ASTRA.com", "admin123", "Operational Manager", "Admin", "Level 3", "Plant Operations Coordinator", None),
                ("maint@ASTRA.com", "maint123", "Ronny Prasad", "Maintenance", "Level 2", "Lead Maintenance Specialist", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256&h=256"),
                ("operator@ASTRA.com", "op123", "Floor Operator", "Operator", "Level 1", "Field Systems Operator", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=256&h=256")
            ]
            cursor.executemany("""
                INSERT INTO users (email, password, name, role, clearance, title, avatar)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, users_to_seed)
            conn.commit()

        # Check if telemetry table is empty
        cursor.execute("SELECT COUNT(*) FROM telemetry")
        count = cursor.fetchone()[0]
        if count == 0:
            print("[DBManager] Telemetry table is empty. Seeding with historical CSV data...")
            self.seed_historical_data(conn)

        # Check if work_orders table is empty
        cursor.execute("SELECT COUNT(*) FROM work_orders")
        wo_count = cursor.fetchone()[0]
        if wo_count == 0:
            print("[DBManager] Work orders table is empty. Seeding with historical work orders...")
            cursor.executemany("""
                INSERT INTO work_orders (id, asset_id, asset_name, description, status, created_at, assigned_tech)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                ("WO-8821", "ASTRA-MTR-101", "Motor M-101 (Conveyor Drive)", "Replace outer race bearing assembly", "Completed", "2026-07-01 10:00:00", "J. Sutherland"),
                ("WO-8902", "ASTRA-MTR-204", "Motor M-204 (Cooling Fan)", "Lubricate gearbox bearing drive", "Completed", "2026-07-05 14:30:00", "M. Rossi"),
                ("WO-8905", "ASTRA-MTR-300", "Motor M-300 (Water Pump)", "Calibrate telemetry transmitter speed loop", "Completed", "2026-07-09 09:15:00", "S. O'Brien")
            ])
            conn.commit()
        conn.close()

    def seed_historical_data(self, conn):
        """Seeds the database with the last 100 entries of the historical CSV files for ASTRA machines."""
        syn_dir = os.path.join(self.db_dir, "synthetic")
        csv_mappings = {
            "ASTRA-MTR-101": ("pump_data.csv", "vibration_rms_mm_s", "stator_current_A", "bearing_temperature_C"),
            "ASTRA-MTR-204": ("mixer_data.csv", "vibration_rms_x_mm_s", "stator_current_A", "gearbox_temperature_C"),
            "ASTRA-MTR-300": ("compressor_data.csv", "vibration_DE_rms_mm_s", "stator_current_A", "bearing_temperature_C"),
            "ASTRA-MTR-305": ("spray_dryer_data.csv", "vibration_rms_mm_s", "feed_pump_current_A", "outlet_air_temperature_C"),
        }

        for machine_id, (filename, vib_col, cur_col, temp_col) in csv_mappings.items():
            path = os.path.join(syn_dir, filename)
            if not os.path.exists(path):
                print(f"[DBManager] [WARNING] Could not find seed file: {path}")
                continue

            df = pd.read_csv(path).tail(100)
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                # Extract values with default fallbacks
                vib = float(row[vib_col]) if vib_col in row else 0.2
                cur = float(row[cur_col]) if cur_col in row else 1.2
                temp = float(row[temp_col]) if temp_col in row else 80.0
                # Using 100.0 as baseline flow rate representing 2000 RPM (2000/20 = 100)
                flw = float(row["flow_rate_lpm"]) if "flow_rate_lpm" in row else 100.0
                
                cursor.execute("""
                    INSERT INTO telemetry (machine_id, vibration_rms, motor_current, temperature, flow_rate)
                    VALUES (%s, %s, %s, %s, %s)
                """, (machine_id, vib, cur, temp, flw))
            
            conn.commit()
            print(f"[DBManager] Seeded 100 records for {machine_id}")

    def clean_and_validate(self, machine_id: str, vibration_rms: float, motor_current: float, temperature: float, flow_rate: float):
        """
        Automated Preprocessing & Data Quality Pipeline:
        1. Handles missing values (imputes from the last known state).
        2. Schema and type validation.
        3. Cleans outliers by clipping them to physical motor boundaries.
        """
        # 1. Fetch last known state for forward-fill imputation
        last_state = self.get_latest_reading(machine_id)
        
        # Helper to impute null values
        def impute(val, key):
            if val is None or pd.isna(val):
                return last_state.get(key, 0.0) if last_state else 0.0
            return float(val)

        v = impute(vibration_rms, "vibration_rms")
        c = impute(motor_current, "motor_current")
        t = impute(temperature, "temperature")
        f = impute(flow_rate, "flow_rate")

        # 2. Outlier boundaries (Clipping to physical constraints)
        v = max(0.01, min(12.0, v))    # Vibration: max 12 g / mm/s
        c = max(0.1, min(40.0, c))     # Current: max 40 A
        t = max(-10.0, min(160.0, t))  # Temp: max 160°C
        f = max(10.0, min(250.0, f))   # Speed proxy: max 250 (5000 RPM)

        return v, c, t, f

    def insert_telemetry(self, machine_id: str, vibration_rms: float, motor_current: float, temperature: float, flow_rate: float):
        """Preprocesses the inputs, cleans outliers, and inserts into PostgreSQL database."""
        v, c, t, f = self.clean_and_validate(machine_id, vibration_rms, motor_current, temperature, flow_rate)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry (machine_id, vibration_rms, motor_current, temperature, flow_rate)
            VALUES (%s, %s, %s, %s, %s)
        """, (machine_id, v, c, t, f))
        conn.commit()
        conn.close()

        # ─── AUTO-ALERT SYSTEM ON PARAMETER BREACH ─────────────────────────────
        breach_messages = []
        if t >= 140.0:
            breach_messages.append(f"Temperature reached {t}°C (Limit: 140°C)")
        if v >= 8.0:
            breach_messages.append(f"Vibration RMS reached {v} mm/s (Limit: 8.0 mm/s)")
        if c >= 15.0:
            breach_messages.append(f"Motor current reached {c} A (Limit: 15.0 A)")

        if breach_messages:
            details_str = ", ".join(breach_messages)
            print(f"[ALERT-BREACH] Safety threshold violated on {machine_id}: {details_str}!")
            try:
                from src.api.notifier import trigger_alert_notifications
                trigger_alert_notifications(
                    machine_id=machine_id,
                    alert_type="safety_limit_breach",
                    title="SAFETY CRITICAL LIMIT BREACH",
                    details=f"Machine {machine_id} critical thresholds breached: {details_str}.",
                    force=False  # Cooldown rate-limit applies (5 mins)
                )
            except Exception as e:
                print(f"[ALERT-BREACH] Failed to auto-dispatch notifications: {e}")

        return v, c, t, f

    def get_latest_reading(self, machine_id: str) -> dict:
        """Retrieves the absolute latest telemetry row for a machine."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM telemetry WHERE machine_id = %s ORDER BY id DESC LIMIT 1
        """, (machine_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def get_recent_history(self, machine_id: str, limit: int = 100) -> list[dict]:
        """Retrieves the recent history of telemetry rows for a machine (oldest first)."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM (
                SELECT * FROM telemetry WHERE machine_id = %s ORDER BY id DESC LIMIT %s
            ) AS sub ORDER BY id ASC
        """, (machine_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_work_orders(self) -> list[dict]:
        """Retrieves all work orders from the database, newest first."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM work_orders ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_work_order(self, asset_id: str, asset_name: str, description: str, assigned_tech: str = 'Unassigned') -> dict:
        """Creates a new work order with a sequential ID (e.g. WO-9103) and inserts it."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Determine next ID
        cursor.execute("SELECT id FROM work_orders WHERE id LIKE 'WO-%'")
        ids = [r[0] for r in cursor.fetchall()]
        
        next_num = 9101
        for wo_id in ids:
            try:
                num = int(wo_id.split('-')[1])
                if num >= next_num:
                    next_num = num + 1
            except (IndexError, ValueError):
                continue
                
        new_id = f"WO-{next_num}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO work_orders (id, asset_id, asset_name, description, status, created_at, assigned_tech)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (new_id, asset_id, asset_name, description, "Pending", created_at, assigned_tech))
        conn.commit()
        conn.close()
        
        return {
            "id": new_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "description": description,
            "status": "Pending",
            "created_at": created_at,
            "assigned_tech": assigned_tech
        }

    def get_notification_settings(self) -> dict:
        """Retrieves the notification settings from the database (id=1)."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {}

    def save_notification_settings(self, s: dict) -> None:
        """Saves the notification settings (upserting id=1)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notification_settings (
                id, smtp_server, smtp_port, sender_email, sender_password, recipient_email,
                twilio_account_sid, twilio_auth_token, twilio_whatsapp_from, recipient_whatsapp,
                whatsapp_provider, waha_server_url, email_enabled
            ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                smtp_server = EXCLUDED.smtp_server,
                smtp_port = EXCLUDED.smtp_port,
                sender_email = EXCLUDED.sender_email,
                sender_password = EXCLUDED.sender_password,
                recipient_email = EXCLUDED.recipient_email,
                twilio_account_sid = EXCLUDED.twilio_account_sid,
                twilio_auth_token = EXCLUDED.twilio_auth_token,
                twilio_whatsapp_from = EXCLUDED.twilio_whatsapp_from,
                recipient_whatsapp = EXCLUDED.recipient_whatsapp,
                whatsapp_provider = EXCLUDED.whatsapp_provider,
                waha_server_url = EXCLUDED.waha_server_url,
                email_enabled = EXCLUDED.email_enabled
        """, (
            s.get("smtp_server"),
            s.get("smtp_port"),
            s.get("sender_email"),
            s.get("sender_password"),
            s.get("recipient_email"),
            s.get("twilio_account_sid"),
            s.get("twilio_auth_token"),
            s.get("twilio_whatsapp_from"),
            s.get("recipient_whatsapp"),
            s.get("whatsapp_provider", "twilio"),
            s.get("waha_server_url", "http://localhost:3000"),
            s.get("email_enabled") if s.get("email_enabled") is not None else True
        ))
        conn.commit()
        conn.close()

    def verify_user(self, email: str, password: str) -> dict:
        """Verifies email/password and returns user dictionary if matched, else None."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT email, name, role, clearance, title, avatar FROM users WHERE LOWER(email) = LOWER(%s) AND password = %s", (email.strip(), password))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[DBManager] Error verifying user: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def update_work_order(self, wo_id: str, status: str, description: str = None, assigned_tech: str = None) -> bool:
        """Updates the status and optionally description/assigned_tech of an existing work order."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            
            updates.append("status = %s")
            params.append(status)
            
            if description is not None:
                updates.append("description = %s")
                params.append(description)
                
            if assigned_tech is not None:
                updates.append("assigned_tech = %s")
                params.append(assigned_tech)
                
            params.append(wo_id)
            
            query = f"UPDATE work_orders SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DBManager] Error updating work order {wo_id}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def delete_work_order(self, wo_id: str) -> bool:
        """Deletes a work order from the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM work_orders WHERE id = %s", (wo_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DBManager] Error deleting work order {wo_id}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def update_user_profile(self, email: str, name: str, title: str, new_email: str, avatar: str = None) -> bool:
        """Updates user details in the users table."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET name = %s, title = %s, email = %s, avatar = %s
                WHERE LOWER(email) = LOWER(%s)
            """, (name, title, new_email, avatar, email))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DBManager] Error updating user profile for {email}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
