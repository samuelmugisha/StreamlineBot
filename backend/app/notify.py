"""Email delivery for escalation notifications.

EMAIL_BACKEND=console (default) logs the email instead of sending it, so the
escalation flow can be tested before AdminIE's SMTP credentials are available.
EMAIL_BACKEND=smtp sends the email via the configured SMTP server.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str) -> None:
    recipient = os.environ.get("ESCALATION_EMAIL_TO")
    backend = os.environ.get("EMAIL_BACKEND", "console")

    if backend != "smtp":
        logger.info(
            "[escalation email — console mode]\nTo: %s\nSubject: %s\n\n%s",
            recipient or "(ESCALATION_EMAIL_TO not set)", subject, body,
        )
        return

    if not recipient:
        logger.warning("EMAIL_BACKEND=smtp but ESCALATION_EMAIL_TO is not set — skipping email.")
        return

    sender = os.environ["SMTP_USERNAME"]
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587))) as server:
        server.starttls()
        server.login(sender, os.environ["SMTP_PASSWORD"])
        server.sendmail(sender, [recipient], msg.as_string())

    logger.info("Escalation email sent to %s", recipient)
