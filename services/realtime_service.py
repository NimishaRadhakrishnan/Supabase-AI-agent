"""
Realtime Service — Listens for Supabase changes and pushes notifications.
"""

import asyncio
import logging
import json
import threading
from config import config
from supabase import create_async_client
from services.email_service import send_change_email

logger = logging.getLogger(__name__)


def send_notification_from_thread(app, msg):
    """
    Called from the Supabase Realtime background thread.
    Schedules a message to be sent via the python-telegram-bot's JobQueue.
    """
    async def send_job(context):
        # We use asynchronous context.bot.send_message
        await context.bot.send_message(
            chat_id=config.MANAGER_TELEGRAM_ID,
            text=context.job.data,
            parse_mode="Markdown"
        )
    app.job_queue.run_once(send_job, 0, data=msg)


def start_realtime_listener(app):
    """Starts listening to Supabase realtime events."""
    if not config.MANAGER_TELEGRAM_ID and not config.MANAGER_EMAIL:
        logger.warning("Neither MANAGER_TELEGRAM_ID nor MANAGER_EMAIL set. Notifications mostly disabled.")
        return

    logger.info("Starting Supabase Realtime listener...")

    def callback(payload):
        try:
            # Parse payload from Supabase Realtime API
            # Payload looks like: {'type': 'INSERT', 'table': 'users', 'schema': 'public', 'record': {...}}
            event = payload.get("type", "UNKNOWN")
            table = payload.get("table", "unknown")
            record = payload.get("record", {})
            old_record = payload.get("old_record", {})

            # Prepare Telegram Markdown Message
            msg = f"🔔 *Database Change Detected*\n"
            msg += f"• *Table*: `{table}`\n"
            msg += f"• *Event*: `{event}`\n\n"

            # Prepare Email HTML Message
            email_subject = f"Database Alert: {event} on {table}"
            email_html = f"<h2>🔔 Database Change Detected</h2>"
            email_html += f"<ul><li><b>Table:</b> {table}</li><li><b>Event:</b> {event}</li></ul>"

            if event in ("INSERT", "UPDATE") and record:
                # Telegram Format
                msg += "📋 *New Data*:\n```\n"
                msg += f"{'Column':<20} | {'Value'}\n"
                msg += "-" * 40 + "\n"
                
                # Email Format
                email_html += "<h3>📋 New Data:</h3>"
                email_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
                email_html += "<tr><th style='text-align: left;'>Column</th><th style='text-align: left;'>Value</th></tr>"

                for k, v in record.items():
                    val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    # Truncate long values for Telegram
                    tg_val_str = val_str[:27] + "..." if len(val_str) > 30 else val_str
                    msg += f"{str(k):<20} | {tg_val_str}\n"
                    
                    # Add to Email HTML
                    email_html += f"<tr><td>{k}</td><td>{val_str}</td></tr>"

                msg += "```"
                email_html += "</table>"
            elif event == "DELETE" and old_record:
                # Telegram Format
                msg += f"🗑️ *Deleted Data*:\n`{old_record}`"
                
                # Email Format
                email_html += "<h3>🗑️ Deleted Data:</h3>"
                email_html += f"<pre>{json.dumps(old_record, indent=2)}</pre>"

            logger.info(f"Database change: {event} on {table}")
            
            # Dispatch to Telegram
            if config.MANAGER_TELEGRAM_ID:
                send_notification_from_thread(app, msg)
                
            # Dispatch to Email
            if config.MANAGER_EMAIL and config.SMTP_SERVER:
                send_change_email(email_subject, email_html)

        except Exception as e:
            logger.error(f"Error in realtime callback: {e}", exc_info=True)

    async def _listen_async():
        try:
            rt_client = await create_async_client(
                config.SUPABASE_URL,
                config.SUPABASE_SERVICE_ROLE_KEY,
            )
            channel = rt_client.channel("db-changes")
            channel.on_postgres_changes(
                event="*",
                callback=callback,
                table="*",
                schema="public",
            )
            await channel.subscribe()
            logger.info("Successfully subscribed to Supabase Realtime.")
            await asyncio.Event().wait()
        except Exception as e:
            logger.error(f"Realtime listener failed: {e}", exc_info=True)

    def _listener_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_listen_async())

    thread = threading.Thread(target=_listener_thread, daemon=True)
    thread.start()
