import os
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://rasyaad:Sellevolerei1@localhost:5432/astra_predictive_maintenance')
with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_sensor_data'")).fetchall()
    print("Columns:", [r[0] for r in res])
