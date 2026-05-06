"""
Email Service — Sends HTML emails formatted as tables for database changes.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config

logger = logging.getLogger(__name__)

def send_change_email(subject: str, html_content: str):
    """
    Synchronously sends an email using smtplib.
    Called from a background thread via the realtime listener.
    """
    if not all([config.SMTP_SERVER, config.SMTP_USERNAME, config.SMTP_PASSWORD, config.MANAGER_EMAIL, config.SENDER_EMAIL]):
        logger.warning("SMTP configuration is incomplete. Skipping email notification.")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = config.SENDER_EMAIL
        msg["To"] = config.MANAGER_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Successfully sent database change email to {config.MANAGER_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}", exc_info=True)
