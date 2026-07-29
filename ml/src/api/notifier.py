import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
import urllib.parse
import json
import time
import socket


# Add project root to sys path to resolve local config overrides
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

# Configurable settings (can be overridden by environment variables or direct code edits)
SMTP_SERVER = os.getenv("ASTRA_SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("ASTRA_SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("ASTRA_SENDER_EMAIL", "").strip()
SENDER_PASSWORD = os.getenv("ASTRA_SENDER_PASSWORD", "").strip()
RECIPIENT_EMAIL = os.getenv("ASTRA_RECIPIENT_EMAIL", "").strip()

# Twilio WhatsApp API Credentials
TWILIO_ACCOUNT_SID = os.getenv("ASTRA_TWILIO_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("ASTRA_TWILIO_TOKEN", "").strip()
TWILIO_WHATSAPP_FROM = os.getenv("ASTRA_TWILIO_WHATSAPP_FROM", "+14155238886").strip()  # Twilio Sandbox number
RECIPIENT_WHATSAPP = os.getenv("ASTRA_RECIPIENT_WHATSAPP", "").strip()    # User's phone number

_last_notified = {}  # key: machine_id + alert_type, value: timestamp
_last_whatsapp_sent_time = 0.0
_email_disabled_by_limit = False

def get_active_settings():
    # Load defaults from environment variables (overridden by local_config.py)
    settings = {
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "sender_email": SENDER_EMAIL,
        "sender_password": SENDER_PASSWORD,
        "recipient_email": RECIPIENT_EMAIL,
        "twilio_account_sid": TWILIO_ACCOUNT_SID,
        "twilio_auth_token": TWILIO_AUTH_TOKEN,
        "twilio_whatsapp_from": TWILIO_WHATSAPP_FROM,
        "recipient_whatsapp": RECIPIENT_WHATSAPP,
        "whatsapp_provider": os.getenv("ASTRA_WHATSAPP_PROVIDER", "twilio").strip(),
        "waha_server_url": os.getenv("ASTRA_WAHA_SERVER_URL", "http://localhost:3000").strip(),
        "email_enabled": True
    }

    # Attempt to load from PostgreSQL
    try:
        import psycopg2
        import psycopg2.extras
        # Use same credentials as DBManager
        conn = psycopg2.connect(
            host=os.getenv("ASTRA_DB_HOST", "localhost"),
            port=int(os.getenv("ASTRA_DB_PORT", "5432")),
            database=os.getenv("ASTRA_DB_NAME", "astra_predictive_maintenance"),
            user=os.getenv("ASTRA_DB_USER", "postgres"),
            password=os.getenv("ASTRA_DB_PASSWORD", "")
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            db_settings = dict(row)
            for k, v in db_settings.items():
                if k == 'id':
                    continue
                if isinstance(v, str):
                    v = v.strip()
                # Overlay if not empty and not a default placeholder
                if isinstance(v, bool):
                    settings[k] = v
                    continue
                val_str = str(v).lower()
                is_placeholder = (
                    "placeholder" in val_str or 
                    "your-app-password" in val_str or 
                    "your_twilio_sid" in val_str or
                    "your-app" in val_str or
                    "@example.com" in val_str
                )
                if v and str(v).strip() and not is_placeholder:
                    # Env-var set explicitly in local_config.py takes priority over DB
                    # for sensitive credentials (password fields). This prevents a wrong
                    # password saved in DB from overriding the correct one from env.
                    env_map = {
                        "sender_password": "ASTRA_SENDER_PASSWORD",
                        "sender_email": "ASTRA_SENDER_EMAIL",
                        "recipient_email": "ASTRA_RECIPIENT_EMAIL",
                        "smtp_server": "ASTRA_SMTP_SERVER",
                    }
                    env_key = env_map.get(k)
                    if env_key:
                        env_val = os.getenv(env_key, "").strip()
                        if env_val:
                            # Env var is explicitly set — keep it, skip DB value
                            continue
                    settings[k] = v
    except Exception as e:
        print(f"[Notifier] Failed to load settings from DB, falling back to environment/defaults: {e}")
    
    return settings

def send_email(subject: str, body: str):
    global _email_disabled_by_limit
    if _email_disabled_by_limit:
        # Silently skip to avoid spamming the console logs
        return False

    settings = get_active_settings()
    if not settings.get("email_enabled", True):
        # Email disabled by user toggle
        return False
    sender_password = settings.get("sender_password")
    sender_email = settings.get("sender_email")
    recipient_email = settings.get("recipient_email")
    smtp_server = settings.get("smtp_server")
    smtp_port = settings.get("smtp_port")

    if sender_password == "your-app-password" or not sender_password or "placeholder" in str(sender_password):
        print("[Notifier] SMTP password not configured. Email notification skipped.")
        return False
    if not smtp_server:
        print("[Notifier] SMTP server not configured. Email notification skipped.")
        return False
    if not sender_email or not recipient_email:
        print("[Notifier] SMTP sender or recipient email not configured. Email notification skipped.")
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
    except socket.gaierror as e:
        print(f"[Notifier] Failed to send email: DNS resolution failed for '{smtp_server}'. Please check your network connection or SMTP server configuration. Details: {e}")
        return False
    except smtplib.SMTPResponseException as e:
        err_msg = str(e.smtp_error)
        if e.smtp_code == 550 or "sending limit" in err_msg.lower() or "limit exceeded" in err_msg.lower():
            _email_disabled_by_limit = True
            print(f"[Notifier] Gmail SMTP Error: {e.smtp_code} - {err_msg}")
            print("[Notifier] Gmail daily sending limit exceeded. Email notifications will be suspended for this session to prevent log spam.")
        else:
            print(f"[Notifier] Failed to send email (SMTP response exception): {e}")
        return False
    except Exception as e:
        err_str = str(e)
        if "550" in err_str and ("sending limit" in err_str.lower() or "limit exceeded" in err_str.lower()):
            _email_disabled_by_limit = True
            print(f"[Notifier] Gmail daily sending limit exceeded error detected: {e}")
            print("[Notifier] Email notifications will be suspended for this session to prevent log spam.")
        else:
            print(f"[Notifier] Failed to send email: {e}")
        return False

def send_whatsapp(body: str):
    global _last_whatsapp_sent_time
    settings = get_active_settings()
    provider = settings.get("whatsapp_provider", "twilio")
    recipient_whatsapp = settings.get("recipient_whatsapp")

    if not recipient_whatsapp:
        print("[Notifier] Recipient WhatsApp number not configured. Notification skipped.")
        return False

    recipient_whatsapp = str(recipient_whatsapp).strip()
    if recipient_whatsapp.startswith("08"):
        recipient_whatsapp = "+62" + recipient_whatsapp[1:]

    # Apply global 2-second delay to avoid Twilio 429 rate limit errors
    now = time.time()
    elapsed = now - _last_whatsapp_sent_time
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)
    _last_whatsapp_sent_time = time.time()

    if provider == "waha":
        waha_url = settings.get("waha_server_url", "http://localhost:3000")
        if not waha_url or "placeholder" in str(waha_url):
            print("[Notifier] WAHA server URL not configured. Notification skipped.")
            return False

        clean_number = recipient_whatsapp.replace("+", "").replace(" ", "").replace("-", "")
        url = waha_url.rstrip("/") + "/api/sendText"

        payload = {
            "chatId": f"{clean_number}@c.us",
            "text": body
        }
        data = json.dumps(payload).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")

            api_key = settings.get("twilio_auth_token")
            if api_key and api_key != "token_placeholder" and "placeholder" not in str(api_key):
                req.add_header("X-Api-Key", api_key)
                req.add_header("Authorization", f"Bearer {api_key}")

            with urllib.request.urlopen(req) as response:
                if response.status in [200, 201]:
                    print("[Notifier] WhatsApp notification sent successfully via WAHA/Evolution API.")
                    return True
                else:
                    print(f"[Notifier] WAHA API returned status: {response.status}")
                    return False
        except Exception as e:
            print(f"[Notifier] Failed to send WAHA WhatsApp message: {e}")
            return False

    elif provider == "callmebot":
        apikey = settings.get("twilio_auth_token")
        if not apikey or apikey == "token_placeholder" or "placeholder" in str(apikey):
            print("[Notifier] CallMeBot API key not configured. WhatsApp skipped.")
            return False
            
        clean_number = recipient_whatsapp.replace("+", "").replace(" ", "").replace("-", "")
        encoded_message = urllib.parse.quote(body)
        url = f"https://api.callmebot.com/whatsapp.php?phone={clean_number}&text={encoded_message}&apikey={apikey}"
        
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print("[Notifier] WhatsApp notification sent successfully via CallMeBot.")
                    return True
                else:
                    print(f"[Notifier] CallMeBot returned status: {response.status}")
                    return False
        except Exception as e:
            print(f"[Notifier] Failed to send CallMeBot WhatsApp: {e}")
            return False

    else:  # Default to 'twilio'
        twilio_sid = settings.get("twilio_account_sid")
        twilio_token = settings.get("twilio_auth_token")
        twilio_from = settings.get("twilio_whatsapp_from")

        if not twilio_sid or twilio_sid == "your_twilio_sid" or "placeholder" in str(twilio_sid):
            print("[Notifier] Twilio credentials not configured. WhatsApp notification skipped.")
            return False
        try:
            if twilio_from:
                twilio_from = str(twilio_from).strip()
                if not twilio_from.startswith("+"):
                    twilio_from = "+" + twilio_from

            if not recipient_whatsapp.startswith("+"):
                recipient_whatsapp = "+" + recipient_whatsapp

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
            print(f"[Notifier] Failed to send WhatsApp message via Twilio: {e}")
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
