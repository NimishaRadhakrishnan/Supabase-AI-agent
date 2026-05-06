import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centralized configuration from environment variables."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Access control
    ALLOWED_USER_IDS: list[int] = []

    # Automation
    MANAGER_TELEGRAM_ID: int = None
    
    # SMTP Email
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    MANAGER_EMAIL: str = os.getenv("MANAGER_EMAIL", "")

    # Approval Server
    APPROVAL_PORT: int = int(os.getenv("APPROVAL_PORT", "8080"))
    APPROVAL_BASE_URL: str = os.getenv("APPROVAL_BASE_URL", "http://localhost:8080")

    def __init__(self):
        raw_ids = os.getenv("ALLOWED_USER_IDS", "")
        if raw_ids.strip():
            self.ALLOWED_USER_IDS = [
                int(uid.strip()) for uid in raw_ids.split(",") if uid.strip()
            ]
        
        manager_id = os.getenv("MANAGER_TELEGRAM_ID", "")
        if manager_id.strip():
            self.MANAGER_TELEGRAM_ID = int(manager_id.strip())

    def validate(self):
        """Validate that all required env vars are set."""
        required = {
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
            "GROQ_API_KEY": self.GROQ_API_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            print("❌ Missing required environment variables:")
            for name in missing:
                print(f"   - {name}")
            print("\n   Copy .env.example to .env and fill in your credentials.")
            raise SystemExit(1)


config = Config()
