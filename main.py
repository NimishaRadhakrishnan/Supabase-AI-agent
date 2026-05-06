"""
Main entry point — Supabase Telegram Agent
"""

import logging
from config import config
from bot import create_bot_app

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # Validate env vars
    config.validate()

    print("──────────────────────────────────────────")
    print("  🤖 Supabase Telegram Agent")
    print("──────────────────────────────────────────")
    print(f"  📡 Supabase: {config.SUPABASE_URL}")
    print(f"  🧠 AI Model: {config.GROQ_MODEL}")
    access = (
        f"Restricted to {len(config.ALLOWED_USER_IDS)} user(s)"
        if config.ALLOWED_USER_IDS
        else "Open to all"
    )
    print(f"  🔒 Access: {access}")
    print("──────────────────────────────────────────")
    print("\n  ✅ Bot is starting... (press Ctrl+C to stop)\n")

    from services.realtime_service import start_realtime_listener
    from services.approval_server import start_approval_server
    
    app = create_bot_app()
    start_realtime_listener(app)
    start_approval_server()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
