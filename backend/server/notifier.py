import os
import requests
import smtplib
from email.mime.text import MIMEText
import smtplib
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")
TARGET_EMAIL = os.getenv("NOTIFY_EMAIL")


# -----------------------------
# Send Slack Notification
# -----------------------------
def notify_slack(message: str):
    if not SLACK_WEBHOOK:
        return

    try:
        requests.post(SLACK_WEBHOOK, json={"text": message})
    except Exception as e:
        print("Slack notification failed:", e)


def send_email(to_email, subject, body):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("❌ Email error: SMTP_EMAIL and SMTP_PASSWORD must be set")
        return
    
    if not to_email:
        print("❌ Email error: to_email cannot be empty")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"📧 Email sent to {to_email}")

    except Exception as e:
        print("❌ Email error:", e)
