"""
Quick test script to verify SMTP email sending works.
Run: python test_email.py
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")

print(f"SMTP_SERVER: {SMTP_SERVER}")
print(f"SMTP_PORT: {SMTP_PORT}")
print(f"SMTP_USERNAME: {SMTP_USERNAME}")
print(f"SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'EMPTY'}")
print(f"SENDER_EMAIL: {SENDER_EMAIL}")
print(f"MANAGER_EMAIL: {MANAGER_EMAIL}")
print()

if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, MANAGER_EMAIL]):
    print("❌ Some SMTP variables are empty! Check your .env file.")
    exit(1)

print("Attempting to send test email...")

try:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = MANAGER_EMAIL
    msg["Subject"] = "🧪 Test Email from Supabase Telegram Bot"

    html = """
    <h2>✅ Email Test Successful!</h2>
    <p>If you are reading this, your SMTP configuration is working correctly.</p>
    <table border='1' cellpadding='5' style='border-collapse: collapse;'>
        <tr><th>Setting</th><th>Status</th></tr>
        <tr><td>SMTP Server</td><td>✅ Connected</td></tr>
        <tr><td>Authentication</td><td>✅ Passed</td></tr>
        <tr><td>Email Delivery</td><td>✅ Sent</td></tr>
    </table>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.set_debuglevel(1)  # Show SMTP conversation
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    print("\n✅ Email sent successfully! Check your inbox.")
except Exception as e:
    print(f"\n❌ Failed to send email: {e}")
