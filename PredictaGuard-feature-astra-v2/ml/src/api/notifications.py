import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import src.api.local_config
except ImportError:
    pass

from src.api.notifier import trigger_alert_notifications, send_email, send_whatsapp


class NotificationService:
    """
    Tiered notification routing based on alert_tier from the Decision Engine.

    Tier         | Email | WhatsApp | Work Order
    -------------|-------|----------|------------
    none         |  ❌   |    ❌    |     ❌
    dashboard_only|  ❌  |    ❌    |     ❌
    email        |  ✅   |    ❌    |     ❌
    full         |  ✅   |    ✅    |     ✅ (logged to console / CMMS)
    """

    def send(self, motor, decision: dict, alert_tier: str = None) -> bool:
        """
        Sends alert notification to the appropriate channels based on alert_tier.

        If alert_tier is not provided, it falls back to the tier stored in the
        decision dict, then to a legacy mapping based on severity.
        """
        severity = decision.get('severity', 'NORMAL')

        # Resolve tier — prefer explicit argument, then decision dict, then legacy mapping
        if alert_tier is None:
            alert_tier = decision.get('alert_tier', None)
        if alert_tier is None:
            # Legacy fallback: map old severities to tiers
            _legacy_map = {
                'NORMAL': 'none',
                'WARNING': 'dashboard_only',
                'HIGH_WARNING': 'email',
                'CRITICAL': 'full',
            }
            alert_tier = _legacy_map.get(severity, 'none')

        # No external notifications for dashboard-only tiers
        if alert_tier in ('none', 'dashboard_only'):
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
        consensus_votes = decision.get('consensus_votes', 0)

        title = f"{severity} Alert: {motor_name} ({motor_id})"
        details = (
            f"Machine: {motor_name} located at {location}\n"
            f"Model Severity: {severity} (Alert Tier: {alert_tier})\n"
            f"Health Score: {health:.1f}% | Anomaly Score: {anomaly:.2f}\n"
            f"Remaining Useful Life: {rul:.1f} days\n"
            f"Detected Fault: {fault_type}\n"
            f"Multi-Signal Consensus: {consensus_votes}/3 signals confirmed\n"
            f"Root Cause Analysis: {cause}\n"
            f"Maintenance Instruction: {recommendation}"
        )

        print(f"[Notifications] Tier '{alert_tier}' — triggering for {motor_id} ({severity})...")

        sent_any = False

        try:
            if alert_tier == 'email':
                # HIGH_WARNING: email only, no WhatsApp
                subject = f"⚠️ PredictaGuard High Warning: {title}"
                email_html = self._build_email_html(
                    motor_id=motor_id,
                    title=title,
                    severity=severity,
                    details=details,
                    badge_color='#E67E22',   # Orange for HIGH_WARNING
                )
                sent_any = send_email(subject, email_html)

            elif alert_tier == 'full':
                # CRITICAL: email + WhatsApp + Work Order trigger
                subject = f"🚨 PredictaGuard CRITICAL Alert: {title}"
                email_html = self._build_email_html(
                    motor_id=motor_id,
                    title=title,
                    severity=severity,
                    details=details,
                    badge_color='#ba1a1a',   # Red for CRITICAL
                )
                email_sent = send_email(subject, email_html)

                whatsapp_text = (
                    f"🚨 *PredictaGuard CRITICAL* 🚨\n\n"
                    f"*Machine:* {motor_name} ({motor_id})\n"
                    f"*Location:* {location}\n"
                    f"*Fault:* {fault_type}\n"
                    f"*Health:* {health:.1f}% | *RUL:* {rul:.1f} days\n"
                    f"*Consensus:* {consensus_votes}/3 signals confirmed\n\n"
                    f"*Action:* {recommendation}\n\n"
                    f"⚠️ Inspect immediately and log work order."
                )
                whatsapp_sent = send_whatsapp(whatsapp_text)

                # Log work order trigger (will be picked up by CMMS integration)
                print(f"[Notifications] AUTO WORK ORDER triggered for {motor_id} "
                      f"— fault: {fault_type}, RUL: {rul:.1f} days")

                sent_any = email_sent or whatsapp_sent

            return sent_any

        except Exception as e:
            print(f"[Notifications] Error sending notification for {motor_id}: {e}")
            return False

    def _build_email_html(self, motor_id: str, title: str, severity: str,
                           details: str, badge_color: str = '#ba1a1a') -> str:
        """Builds a styled HTML email body for the alert."""
        details_html = details.replace('\n', '<br>')
        return f"""
<html>
<body style="font-family: 'Inter', sans-serif; line-height: 1.6; color: #1b1c1a; background: #faf9f6; padding: 24px;">
  <div style="max-width: 600px; margin: auto; background: white; border-radius: 8px;
              border: 1px solid #E2DDD6; overflow: hidden;">
    <div style="background: {badge_color}; padding: 16px 24px;">
      <h2 style="color: white; margin: 0; font-size: 18px;">⚠️ PredictaGuard Alert</h2>
      <p style="color: rgba(255,255,255,0.85); margin: 4px 0 0 0; font-size: 13px;">
        Alert Management System — Automated Notification
      </p>
    </div>
    <div style="padding: 24px;">
      <div style="display: inline-block; background: {badge_color}; color: white;
                  padding: 4px 12px; border-radius: 4px; font-size: 11px;
                  font-weight: bold; letter-spacing: 0.05em; margin-bottom: 16px;">
        {severity}
      </div>
      <h3 style="margin: 0 0 16px 0; color: #003720;">{title}</h3>
      <div style="background: #f4f3f0; border-radius: 6px; padding: 16px;
                  font-family: 'JetBrains Mono', monospace; font-size: 13px;
                  line-height: 1.8; border-left: 4px solid {badge_color};">
        {details_html}
      </div>
      <hr style="border: none; border-top: 1px solid #E2DDD6; margin: 24px 0;">
      <p style="font-size: 12px; color: #6B6860; margin: 0;">
        Log in to <a href="http://localhost:8000/" style="color: #1c6b45;">PredictaGuard Dashboard</a>
        to manage alerts and dispatch work orders.
        <br>This notification was triggered by the Alert Management System after
        multi-signal consensus and persistence verification.
      </p>
    </div>
  </div>
</body>
</html>"""
