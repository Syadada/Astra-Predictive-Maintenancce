import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="astra_predictive_maintenance",
    user="rasyaad",
    password="Sellevolerei1"
)
cur = conn.cursor()

# Update settings
cur.execute("""
    UPDATE notification_settings 
    SET whatsapp_provider = 'waha', 
        waha_server_url = 'http://localhost:3000' 
    WHERE id = 1
""")
conn.commit()

# Verify settings
cur.execute("SELECT * FROM notification_settings WHERE id = 1")
row = cur.fetchone()
print("Updated notification settings in DB:")
print(row)

conn.close()
