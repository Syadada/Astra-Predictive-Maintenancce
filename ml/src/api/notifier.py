import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
import urllib.parse
import json
import time

try:
    import src.api.local_config
except ImportError:
    pass

# Configurable settings (can be overridden by environment variables or direct code edits)
SMTP_SERVER = os.getenv("ASTRA_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("ASTRA_SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("ASTRA_SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("ASTRA_SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("ASTRA_RECIPIENT_EMAIL", "")

# Twilio WhatsApp API Credentials
TWILIO_ACCOUNT_SID = os.getenv("ASTRA_TWILIO_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("ASTRA_TWILIO_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("ASTRA_TWILIO_WHATSAPP_FROM", "+14155238886")  # Twilio Sandbox number
RECIPIENT_WHATSAPP = os.getenv("ASTRA_RECIPIENT_WHATSAPP", "")    # User's phone number

_last_notified = {}  # key: machine_id + alert_type, value: timestamp

def get_active_settings():
    # Attempt to load from PostgreSQL
    try:
        import psycopg2
        import psycopg2.extras
        # Use same credentials as DBManager
        conn = psycopg2.connect(
            host=os.getenv("ASTRA_DB_HOST", "localhost"),
            port=int(os.getenv("ASTRA_DB_PORT", "5432")),
            database=os.getenv("ASTRA_DB_NAME", "postgres"),
            user=os.getenv("ASTRA_DB_USER", "postgres"),
            password=os.getenv("ASTRA_DB_PASSWORD", "")
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        print(f"[Notifier] Failed to load settings from DB, falling back to environment/defaults: {e}")
    
    # Fallback to module-level or environment variables
    return {
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "sender_email": SENDER_EMAIL,
        "sender_password": SENDER_PASSWORD,
        "recipient_email": RECIPIENT_EMAIL,
        "twilio_account_sid": TWILIO_ACCOUNT_SID,
        "twilio_auth_token": TWILIO_AUTH_TOKEN,
        "twilio_whatsapp_from": TWILIO_WHATSAPP_FROM,
        "recipient_whatsapp": RECIPIENT_WHATSAPP
    }

def send_email(subject: str, body: str):
    settings = get_active_settings()
    sender_password = settings.get("sender_password")
    sender_email = settings.get("sender_email")
    recipient_email = settings.get("recipient_email")
    smtp_server = settings.get("smtp_server")
    smtp_port = settings.get("smtp_port")

    if sender_password == "your-app-password" or not sender_password:
        print("[Notifier] SMTP password not configured. Email notification skipped.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"[Notifier] Email alert successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send email: {e}")
        return False

def send_whatsapp(body: str):
    settings = get_active_settings()
    twilio_sid = settings.get("twilio_account_sid")
    twilio_token = settings.get("twilio_auth_token")
    twilio_from = settings.get("twilio_whatsapp_from")
    recipient_whatsapp = settings.get("recipient_whatsapp")

    if twilio_sid == "your_twilio_sid" or not twilio_sid:
        print("[Notifier] Twilio credentials not configured. WhatsApp notification skipped.")
        return False
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
        data = urllib.parse.urlencode({
            "From": f"whatsapp:{twilio_from}",
            "To": f"whatsapp:{recipient_whatsapp}",
            "Body": body
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method="POST")
        
        import base64
        auth_str = f"{twilio_sid}:{twilio_token}"
        encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {encoded_auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"[Notifier] WhatsApp message sent! SID: {res_data.get('sid')}")
            return True
    except Exception as e:
        print(f"[Notifier] Failed to send WhatsApp message: {e}")
        return False

def trigger_alert_notifications(machine_id: str, alert_type: str, title: str, details: str, force: bool = False):
    key = f"{machine_id}:{alert_type}"
    now = time.time()
    
    # 5-minute cooldown per machine/alert type to prevent spamming
    if not force and key in _last_notified and (now - _last_notified[key]) < 300:
        return
        
    _last_notified[key] = now
    
    subject = f"⚠️ Project ASTRA Critical Alert: {title}"
    email_html = f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.5; color: #1b1c1a;">
        <h2 style="color: #ba1a1a;">⚠️ ASTRA Critical Winding/Sensor Exception</h2>
        <p>A critical anomaly has been detected on the machine sensor stream.</p>
        <hr/>
        <p><strong>Machine ID:</strong> {machine_id}</p>
        <p><strong>Alert Event:</strong> {title}</p>
        <p><strong>Status:</strong> CRITICAL</p>
        <p><strong>Event Details:</strong> {details}</p>
        <hr/>
        <p style="font-size: 12px; color: #6B6860;">Log in to http://localhost:8000/ to manage alerts and auto-dispatch work orders.</p>
    </body>
    </html>
    """
    
    whatsapp_text = f"⚠️ *Project ASTRA Alert* ⚠️\n\n*Machine:* {machine_id}\n*Alert:* {title}\n*Details:* {details}\n\nInspect immediately!"
    
    send_email(subject, email_html)
    send_whatsapp(whatsapp_text)
