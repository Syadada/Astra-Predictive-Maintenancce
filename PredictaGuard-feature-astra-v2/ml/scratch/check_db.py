import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="astra_predictive_maintenance",
    user="rasyaad",
    password="Sellevolerei1"
)
cur = conn.cursor()

# Get total count of raw sensor data
cur.execute("SELECT COUNT(*) FROM raw_sensor_data")
print("Total raw rows:", cur.fetchone()[0])

# Get unprocessed row count for each motor
cur.execute("SELECT motor_id, MAX(window_end) FROM feature_windows GROUP BY motor_id")
feature_ends = dict(cur.fetchall())

for mid in ['MTR-01', 'MTR-02', 'MTR-03', 'MTR-04', 'MTR-05', 'MTR-06']:
    last_p = feature_ends.get(mid)
    if last_p:
        cur.execute("SELECT COUNT(*) FROM raw_sensor_data WHERE motor_id = %s AND recorded_at > %s", (mid, last_p))
        unprocessed = cur.fetchone()[0]
        print(f"Motor {mid}: {unprocessed} unprocessed rows (last processed: {last_p})")
    else:
        cur.execute("SELECT COUNT(*) FROM raw_sensor_data WHERE motor_id = %s", (mid,))
        unprocessed = cur.fetchone()[0]
        print(f"Motor {mid}: {unprocessed} unprocessed rows (never processed)")

conn.close()
