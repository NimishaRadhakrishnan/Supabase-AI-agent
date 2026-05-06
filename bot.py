"""
Telegram Bot — Command handlers and natural language processing.
Uses python-telegram-bot (v21+) with async handlers.
"""

import json
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from config import config
from services import supabase_service as db
from services import report_service
from services.agent import process_message, get_table_list_for_context, _send_change_email_async
from services.email_service import send_change_email
from services import approval_server
import threading
import asyncio

logger = logging.getLogger(__name__)

# ─── Shared State ─────────────────────────────────────────────────────
# Point to the storage in approval_server
pending_deletes = approval_server.pending_deletes

# We need a reference to the bot and loop to send messages from approval server thread
_bot_app = None
_main_loop = None


# ─── Access Control ───────────────────────────────────────────────────

def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot."""
    if not config.ALLOWED_USER_IDS:
        return True  # No restrictions
    return user_id in config.ALLOWED_USER_IDS


# ─── /start Command ──────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return

    await update.message.reply_text(
        "🤖 *Supabase Database Agent*\n\n"
        "I can help you manage your Supabase database right from Telegram!\n\n"
        "*Commands:*\n"
        "/tables — List all tables\n"
        "/schema <table> — Show table structure\n"
        "/query <table> — Query data (first 20 rows)\n"
        "/count <table> — Count rows\n"
        "/insert <table> key=value ... — Insert a row\n"
        "/update <table> match | data — Update rows\n"
        "/delete <table> key=value — Delete rows\n"
        "/sql <query> — Execute raw SQL\n"
        "/report — Generate a database manager report\n\n"
        "✨ *Version: 2.1 (Email Approval Enabled)*\n\n"
        "💡 *Or just type in natural language!*\n"
        "Examples:\n"
        '• _"Show me all users"_\n'
        '• _"Add a new product called Widget with price 29.99"_\n'
        '• _"How many orders were placed today?"_\n'
        '• _"Delete the user with id 5"_',
        parse_mode="Markdown",
    )


# ─── /help Command ───────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return

    await update.message.reply_text(
        "📖 *Help Guide*\n\n"
        "*Structured Commands:*\n"
        "/tables — List all database tables\n"
        "/schema users — Show columns & types\n"
        "/query orders — Get first 20 rows\n"
        "/count products — Count total rows\n"
        "/insert users name=John email=john@example.com\n"
        "/update users id=1 | name=Jane\n"
        "/delete users id=1\n"
        "/sql SELECT COUNT(*) FROM orders WHERE status='active'\n"
        "/report — AI generated summary of your database\n\n"
        "*Natural Language:*\n"
        "Just type what you want in plain English!\n"
        "I'll figure out the right database operation.\n\n"
        "_Powered by Groq AI + Supabase_",
        parse_mode="Markdown",
    )


# ─── /report Command ─────────────────────────────────────────────────

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    await update.message.reply_text("📊 Generating AI Manager Report... (This may take a few seconds)")
    try:
        report = await report_service.generate_manager_report()
        await _send_long_message(update, report)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /tables Command ─────────────────────────────────────────────────

async def tables_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    await update.message.reply_text("⏳ Fetching tables...")
    try:
        tables = await db.list_tables()
        if not tables:
            await update.message.reply_text("📭 No tables found in the database.")
        else:
            table_list = "\n".join(f"  {i+1}. `{t}`" for i, t in enumerate(tables))
            await update.message.reply_text(
                f"📋 *Database Tables* ({len(tables)}):\n\n{table_list}",
                parse_mode="Markdown",
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /schema Command ─────────────────────────────────────────────────

async def schema_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/schema <table_name>`", parse_mode="Markdown"
        )
        return

    table_name = context.args[0]
    await update.message.reply_text(
        f"⏳ Fetching schema for `{table_name}`...", parse_mode="Markdown"
    )
    try:
        schema = await db.get_table_schema(table_name)
        if not schema:
            await update.message.reply_text(
                f"❌ Table `{table_name}` not found or has no columns.",
                parse_mode="Markdown",
            )
            return

        def _format_col(col):
            line = f"• `{col['column_name']}` — {col['data_type']}"
            if col.get("is_nullable") == "NO":
                line += "  (NOT NULL)"
            if col.get("column_default"):
                line += f"  DEFAULT: {col['column_default']}"
            return line

        cols = "\n".join(_format_col(col) for col in schema)
        await update.message.reply_text(
            f"📐 *Schema for `{table_name}`*:\n\n{cols}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /query Command ──────────────────────────────────────────────────

async def query_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/query <table_name>`", parse_mode="Markdown"
        )
        return

    table_name = context.args[0]
    await update.message.reply_text(
        f"⏳ Querying `{table_name}`...", parse_mode="Markdown"
    )
    try:
        rows = await db.query_table(table_name, limit=20)
        if not rows:
            await update.message.reply_text(
                f"📭 No rows found in `{table_name}`.", parse_mode="Markdown"
            )
            return

        text = _format_rows(table_name, rows)
        await _send_long_message(update, text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /count Command ──────────────────────────────────────────────────

async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/count <table_name>`", parse_mode="Markdown"
        )
        return

    table_name = context.args[0]
    try:
        count = await db.get_table_count(table_name)
        await update.message.reply_text(
            f"📊 *`{table_name}`* has *{count}* row(s).", parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /insert Command ─────────────────────────────────────────────────

async def insert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    raw_text = update.message.text
    parts = raw_text.split(maxsplit=2)

    if len(parts) < 3:
        await update.message.reply_text(
            '⚠️ Usage: `/insert <table> key=value key=value ...`\n'
            'Example: `/insert users name=John email=john@example.com`',
            parse_mode="Markdown",
        )
        return

    table_name = parts[1]
    kv_str = parts[2]

    try:
        data = _parse_key_value_pairs(kv_str)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    await update.message.reply_text(
        f"⏳ Inserting into `{table_name}`...", parse_mode="Markdown"
    )
    try:
        result = await db.insert_row(table_name, data)
        _send_change_email_async("INSERT", table_name, result)
        row_text = _format_single_row(result)
        await update.message.reply_text(
            f"✅ *Inserted into `{table_name}`*:\n\n{row_text}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /update Command ─────────────────────────────────────────────────

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    raw_text = update.message.text
    # Format: /update table match_key=value | data_key=value
    parts = raw_text.split(maxsplit=2)

    if len(parts) < 3:
        await update.message.reply_text(
            '⚠️ Usage: `/update <table> match_key=value | data_key=value`\n'
            'Example: `/update users id=1 | name=Jane`',
            parse_mode="Markdown",
        )
        return

    table_name = parts[1]
    rest = parts[2].strip()

    if "|" not in rest:
        await update.message.reply_text(
            "❌ Separate match and data with `|`\n"
            "Example: `/update users id=1 | name=Jane`",
            parse_mode="Markdown",
        )
        return

    match_part, data_part = rest.split("|", 1)
    try:
        match_obj = _parse_key_value_pairs(match_part.strip())
        data_obj = _parse_key_value_pairs(data_part.strip())
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    await update.message.reply_text(
        f"⏳ Updating `{table_name}`...", parse_mode="Markdown"
    )
    try:
        result = await db.update_row(table_name, match_obj, data_obj)
        if not result:
            await update.message.reply_text(
                f"⚠️ No rows matched the criteria in `{table_name}`.",
                parse_mode="Markdown",
            )
        else:
            _send_change_email_async("UPDATE", table_name, result)
            rows_text = _format_result_rows(result)
            await update.message.reply_text(
                f"✅ *Updated {len(result)} row(s) in `{table_name}`*:\n\n{rows_text}",
                parse_mode="Markdown",
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── /delete Command ─────────────────────────────────────────────────

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    raw_text = update.message.text
    parts = raw_text.split(maxsplit=2)

    if len(parts) < 3:
        await update.message.reply_text(
            '⚠️ Usage: `/delete <table> key=value`\n'
            'Example: `/delete users id=1`',
            parse_mode="Markdown",
        )
        return

    table_name = parts[1]
    kv_str = parts[2]

    try:
        match = _parse_key_value_pairs(kv_str)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    # Show what will be deleted, then ask for approval
    await _request_delete_approval(update, table_name, match)


async def _request_delete_approval(update: Update, table_name: str, match: dict):
    """Show data to be deleted, send approval email, and present Approve/Cancel buttons."""
    try:
        # Query matching rows to show the user what will be deleted
        rows = await db.query_table(table_name, filters=match, limit=10)
        if not rows:
            await update.message.reply_text(
                f"⚠️ No rows matched the criteria in `{table_name}`.",
                parse_mode="Markdown",
            )
            return

        # Store pending delete with a unique ID
        request_id = str(uuid.uuid4())[:8]
        pending_deletes[request_id] = {
            "table": table_name,
            "match": match,
            "user_id": update.effective_user.id,
            "chat_id": update.effective_chat.id,
        }

        # Send approval email to admin
        _send_delete_approval_email(table_name, match, rows, request_id)

        # Show matching rows (NO Telegram buttons)
        rows_text = _format_result_rows(rows)
        match_text = ", ".join(f"{k}={v}" for k, v in match.items())
        await update.message.reply_text(
            f"⚠️ *Delete Requested — `{table_name}`* (where {match_text})\n\n"
            f"The following {len(rows)} row(s) will be deleted:\n\n{rows_text}\n\n"
            f"📧 *Approval buttons have been sent to your email!*\n"
            f"Please check your inbox to Approve or Cancel.",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def _send_delete_approval_email(table_name: str, match: dict, rows: list, request_id: str):
    """Send an email to the admin requesting delete approval with HTML buttons."""
    if not config.MANAGER_EMAIL or not config.SMTP_SERVER:
        return
    try:
        match_text = ", ".join(f"{k}={v}" for k, v in match.items())
        
        # Build approval/cancel links
        approve_url = approval_server.get_approval_url(request_id, "approve")
        cancel_url = approval_server.get_approval_url(request_id, "cancel")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d9534f;">⚠️ Delete Approval Request</h2>
            <p>A user has requested to delete rows from <b>{table_name}</b> where <b>{match_text}</b>.</p>
            
            <p>The following rows (first 10) match the criteria:</p>
        """

        # Build HTML table of rows
        if rows:
            columns = list(rows[0].keys())
            html += "<table border='1' cellpadding='6' style='border-collapse: collapse; font-size: 13px;'>"
            html += "<tr style='background-color: #f2f2f2;'>"
            for col in columns:
                html += f"<th>{col}</th>"
            html += "</tr>"
            for row in rows:
                html += "<tr>"
                for col in columns:
                    val = row.get(col, '')
                    html += f"<td>{val}</td>"
                html += "</tr>"
            html += "</table>"

        # Action Buttons
        html += f"""
            <br><br>
            <div style="margin-top: 20px;">
                <a href="{approve_url}" style="background-color: #5cb85c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 15px;">✅ Approve Delete</a>
                <a href="{cancel_url}" style="background-color: #d9534f; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">❌ Cancel</a>
            </div>
            <p style="color: #777; font-size: 12px; margin-top: 30px;">This link will take you to a local server to confirm the action.</p>
        </body>
        </html>
        """
        
        subject = f"⚠️ Delete Approval Needed: {table_name} (where {match_text})"
        threading.Thread(target=send_change_email, args=(subject, html), daemon=True).start()
    except Exception as e:
        logger.error(f"Failed to build/send approval email: {e}")


# ─── Approval Callback Handling ──────────────────────────────────────

def _handle_approval_from_server(action: str, table_name: str, match: dict, user_id: int, chat_id: int):
    """Callback function called by approval_server (from a background thread)."""
    if _bot_app and _main_loop:
        asyncio.run_coroutine_threadsafe(
            _execute_approval_action(action, table_name, match, chat_id),
            _main_loop
        )

async def _execute_approval_action(action: str, table_name: str, match: dict, chat_id: int):
    """The actual async logic for handling the approval action."""
    try:
        if action == "cancel":
            await _bot_app.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 *Delete Cancelled* — The request for `{table_name}` was rejected via email.",
                parse_mode="Markdown"
            )
            return

        # Execute delete
        result = await db.delete_row(table_name, match)
        _send_change_email_async("DELETE", table_name, result)
        
        rows_text = _format_result_rows(result)
        await _bot_app.bot.send_message(
            chat_id=chat_id,
            text=f"🗑️ *Deleted {len(result)} row(s) from `{table_name}` (Approved via email)*:\n\n{rows_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error executing approved delete: {e}")
        await _bot_app.bot.send_message(chat_id=chat_id, text=f"❌ Error executing approved delete: {e}")



# ─── /sql Command ────────────────────────────────────────────────────

async def sql_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    raw_text = update.message.text
    sql = raw_text.split(maxsplit=1)[1] if len(raw_text.split(maxsplit=1)) > 1 else ""

    if not sql.strip():
        await update.message.reply_text(
            "⚠️ Usage: `/sql <SQL query>`\nExample: `/sql SELECT * FROM users LIMIT 5`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("⏳ Executing SQL...")
    try:
        result = await db.execute_raw_sql(sql)
        text = f"🔧 *SQL Result*:\n\n```\n{json.dumps(result, indent=2, default=str)}\n```"
        await _send_long_message(update, text)
    except Exception as e:
        await update.message.reply_text(f"❌ SQL Error: {e}")


# ─── Natural Language Handler ─────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch-all handler for natural language messages → Groq AI agent."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return

    user_message = update.message.text
    await update.message.reply_text("🧠 Thinking...")

    try:
        table_list = await get_table_list_for_context()
        result = await process_message(user_message, table_list)

        # If the AI returned a pending delete, show approval flow
        if result.get("action") == "pending_delete":
            table_name = result["table"]
            match = result["match"]
            await _request_delete_approval(update, table_name, match)
        else:
            await _send_long_message(update, result["text"])
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Something went wrong: {e}")


# ─── Utility Functions ───────────────────────────────────────────────

def _format_rows(table_name: str, rows: list[dict]) -> str:
    """Format database rows as readable Telegram text."""
    text = f"📊 *`{table_name}`* — {len(rows)} row(s):\n\n"
    max_rows = 10
    display_rows = rows[:max_rows]

    for row in display_rows:
        entries = "\n".join(
            f"  • `{key}`: {_truncate(val)}" for key, val in row.items()
        )
        text += f"──────────────\n{entries}\n"

    if len(rows) > max_rows:
        text += f"\n_...and {len(rows) - max_rows} more row(s)._"

    return text


def _format_single_row(row) -> str:
    """Format a single row (dict or list with one dict) as readable text."""
    if isinstance(row, list):
        row = row[0] if row else {}
    if not isinstance(row, dict):
        return str(row)
    return "\n".join(f"  • `{key}`: {_truncate(val)}" for key, val in row.items())


def _format_result_rows(rows) -> str:
    """Format one or more result rows as readable text."""
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        return "_No data._"
    parts = []
    for row in rows:
        entries = "\n".join(f"  • `{key}`: {_truncate(val)}" for key, val in row.items())
        parts.append(f"──────────────\n{entries}")
    return "\n".join(parts)


def _truncate(val, max_len=100) -> str:
    if val is None:
        return "NULL"
    s = json.dumps(val, default=str) if isinstance(val, (dict, list)) else str(val)
    return s[: max_len - 3] + "..." if len(s) > max_len else s


def _parse_key_value_pairs(text: str) -> dict:
    """Parse 'key=value key2=value2' into a dict.
    
    Supports:
      name=John email=john@example.com  → {"name": "John", "email": "john@example.com"}
      price=29.99 active=true           → {"price": 29.99, "active": true}
      bio="Hello World"                 → {"bio": "Hello World"}
    """
    import shlex
    result = {}
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()

    for token in tokens:
        if "=" not in token:
            raise ValueError(
                f"Invalid format: `{token}`. Use key=value pairs.\n"
                "Example: `name=John email=john@example.com`"
            )
        key, _, value = token.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError("Key cannot be empty in key=value pair.")

        # Auto-convert types
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.lower() == "null" or value.lower() == "none":
            value = None
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass  # keep as string

        result[key] = value

    if not result:
        raise ValueError("No key=value pairs found.")
    return result


async def _send_long_message(update: Update, text: str):
    """Split and send messages exceeding Telegram's 4096 char limit."""
    max_length = 4000
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    remaining = text
    while remaining:
        if len(remaining) <= max_length:
            await update.message.reply_text(remaining, parse_mode="Markdown")
            break
        split_at = remaining.rfind("\n", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            split_at = max_length
        await update.message.reply_text(remaining[:split_at], parse_mode="Markdown")
        remaining = remaining[split_at:]


# ─── Build Application ───────────────────────────────────────────────

def create_bot_app() -> Application:
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tables", tables_command))
    app.add_handler(CommandHandler("schema", schema_command))
    app.add_handler(CommandHandler("query", query_command))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CommandHandler("insert", insert_command))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("sql", sql_command))
    app.add_handler(CommandHandler("report", report_command))

    # Store global references for the approval server
    global _bot_app, _main_loop
    _bot_app = app
    _main_loop = asyncio.get_event_loop()
    approval_server.set_approval_callback(_handle_approval_from_server)

    # Natural language catch-all (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
