import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.api.notifier import trigger_alert_notifications

class NotificationService:
    def send(self, motor, decision):
        """
        Sends alert notification to SMTP and Twilio WhatsApp channels
        based on the Decision Engine output.
        """
        severity = decision.get('severity', 'NORMAL')
        if severity not in ['WARNING', 'CRITICAL']:
            return False

        motor_id = motor.motor_id
        motor_name = getattr(motor, 'name', 'Induction Motor')
        location = getattr(motor, 'location', 'Factory Floor')
        
        health = decision.get('health_score', 100.0)
        anomaly = decision.get('anomaly_score', 0.0)
        rul = decision.get('rul_days', 125.0)
        recommendation = decision.get('recommendation', '')
        fault_type = decision.get('fault_type', 'healthy')
        cause = decision.get('top_cause', 'Unknown')
        
        title = f"{severity} Alert: {motor_name} ({motor_id})"
        details = (
            f"Machine: {motor_name} located at {location}\n"
            f"Model Severity: {severity}\n"
            f"Health Score: {health:.1f}% | Anomaly Score: {anomaly:.2f}\n"
            f"Remaining Useful Life: {rul:.1f} days\n"
            f"Detected Fault: {fault_type}\n"
            f"Root Cause Analysis: {cause}\n"
            f"Maintenance Instruction: {recommendation}"
        )
        
        print(f"[Notifications] Triggering alert for {motor_id}...")
        try:
            trigger_alert_notifications(
                machine_id=motor_id,
                alert_type=severity.lower(),
                title=title,
                details=details,
                force=True  # Ensure alert gets delivered for testing
            )
            return True
        except Exception as e:
            print(f"[Notifications] Error sending notification: {e}")
            return False
