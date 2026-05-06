"""
AI Agent — Groq-powered natural language to database command translator.
Uses Llama 3.3 70B via Groq for blazing-fast inference.
"""

import json
import threading
from groq import Groq
from config import config
from services import supabase_service as db
from services.email_service import send_change_email

groq_client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a database management AI assistant connected to a Supabase PostgreSQL database via a Telegram bot.

Your job is to understand the user's natural language request and convert it into a structured JSON command that the system can execute.

AVAILABLE COMMANDS:
1. list_tables - List all tables in the database
2. table_schema - Get the structure of a specific table
3. query - Query/read data from a table
4. insert - Insert a new row into a table
5. update - Update existing rows in a table
6. delete - Delete rows from a table
7. count - Count rows in a table
8. raw_sql - Execute raw SQL (use sparingly, only when other commands can't do the job)

RESPONSE FORMAT - Always respond with valid JSON:
{
  "command": "command_name",
  "params": { ... },
  "explanation": "Brief explanation of what you're doing"
}

COMMAND PARAMS:

list_tables: {} (no params needed)

table_schema: { "table": "table_name" }

query: {
  "table": "table_name",
  "filters": { "column": "value" },
  "limit": 20,
  "offset": 0,
  "order_by": "column_name",
  "ascending": true
}

insert: {
  "table": "table_name",
  "data": { "column1": "value1", "column2": "value2" }
}

update: {
  "table": "table_name",
  "match": { "id": 1 },
  "data": { "column1": "new_value" }
}

delete: {
  "table": "table_name",
  "match": { "id": 1 }
}

count: { "table": "table_name" }

raw_sql: { "sql": "SELECT ..." }

FILTER OPERATORS (for query command):
- Simple equality: { "column": "value" }
- Greater than: { "column": { "gt": 5 } }
- Less than: { "column": { "lt": 10 } }
- Like: { "column": { "ilike": "%search%" } }
- Not equal: { "column": { "neq": "value" } }
- In list: { "column": { "in": [1, 2, 3] } }

IMPORTANT RULES:
- If the user's request is unclear, set command to "clarify" with an explanation field asking what they mean
- For INSERT commands: You will be given table schemas. If the user has NOT provided values for all required (NOT NULL) columns that lack defaults, set command to "clarify" and list the missing required columns so the user can provide them. Do NOT attempt an insert with missing required fields.
- Always try to use the most specific command rather than raw_sql
- For ambiguous table names, try your best guess but mention it in the explanation
- Never modify or drop system tables
- If the user asks a general question (not database related), set command to "chat" with explanation containing your answer

RESPOND ONLY WITH JSON. No markdown, no code fences, just the JSON object."""


async def process_message(user_message: str, table_list: list[str] = None) -> dict:
    """
    Process a natural language message through Groq and execute the resulting command.
    Returns dict with 'text' key containing the formatted response.
    """
    context = ""
    if table_list:
        context = f"\n\nCURRENT DATABASE TABLES: {', '.join(table_list)}"

        # Fetch schemas for all tables so the AI knows required columns
        schema_parts = []
        for tbl in table_list:
            try:
                schema = await db.get_table_schema(tbl)
                if schema:
                    cols = []
                    for c in schema:
                        info = f"  - {c['column_name']} ({c['data_type']})"
                        if c.get('is_nullable') == 'NO' and not c.get('column_default'):
                            info += " [REQUIRED]"
                        elif c.get('column_default'):
                            info += f" [DEFAULT: {c['column_default']}]"
                        cols.append(info)
                    schema_parts.append(f"\n{tbl}:\n" + "\n".join(cols))
            except Exception:
                pass
        if schema_parts:
            context += "\n\nTABLE SCHEMAS:" + "".join(schema_parts)

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + context},
                {"role": "user", "content": user_message},
            ],
            model=config.GROQ_MODEL,
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        response_text = chat_completion.choices[0].message.content
        if not response_text:
            return {"text": "❌ No response from AI. Please try again."}

        parsed = json.loads(response_text)
        return await execute_command(parsed)

    except json.JSONDecodeError:
        return {"text": "❌ AI returned an invalid response. Please try rephrasing."}
    except Exception as e:
        return {"text": f"❌ AI error: {e}"}


async def execute_command(parsed: dict) -> dict:
    """Execute a parsed command against the database."""
    command = parsed.get("command", "")
    params = parsed.get("params", {})
    explanation = parsed.get("explanation", "")

    try:
        if command == "list_tables":
            tables = await db.list_tables()
            if not tables:
                return {"text": "📭 No tables found in the database."}
            table_list = "\n".join(f"  {i+1}. `{t}`" for i, t in enumerate(tables))
            return {"text": f"📋 *Database Tables* ({len(tables)}):\n\n{table_list}"}

        elif command == "table_schema":
            schema = await db.get_table_schema(params["table"])
            if not schema:
                return {"text": f"❌ Table `{params['table']}` not found or has no columns."}
            def _fmt_col(c):
                line = f"• `{c['column_name']}` — {c['data_type']}"
                if c.get("is_nullable") == "NO":
                    line += "  (NOT NULL)"
                if c.get("column_default"):
                    line += f"  DEFAULT: {c['column_default']}"
                return line

            cols = "\n".join(_fmt_col(col) for col in schema)
            return {"text": f"📐 *Schema for `{params['table']}`*:\n\n{cols}"}

        elif command == "query":
            rows = await db.query_table(
                params["table"],
                filters=params.get("filters"),
                limit=params.get("limit", 20),
                offset=params.get("offset", 0),
                order_by=params.get("order_by"),
                ascending=params.get("ascending", True),
            )
            if not rows:
                return {"text": f"📭 No rows found in `{params['table']}` matching your criteria."}
            return {"text": format_rows(params["table"], rows)}

        elif command == "insert":
            inserted = await db.insert_row(params["table"], params["data"])
            _send_change_email_async("INSERT", params["table"], inserted)
            row_text = _format_single_row(inserted)
            return {
                "text": f"✅ *Inserted into `{params['table']}`*:\n\n{row_text}"
            }

        elif command == "update":
            updated = await db.update_row(params["table"], params["match"], params["data"])
            if not updated:
                return {"text": f"⚠️ No rows matched the criteria in `{params['table']}`."}
            _send_change_email_async("UPDATE", params["table"], updated)
            rows_text = _format_result_rows(updated)
            return {
                "text": f"✅ *Updated {len(updated)} row(s) in `{params['table']}`*:\n\n{rows_text}"
            }

        elif command == "delete":
            # Don't delete immediately — return pending action for approval flow
            return {
                "text": f"⚠️ Delete requested on `{params['table']}`. Awaiting approval...",
                "action": "pending_delete",
                "table": params["table"],
                "match": params["match"],
            }

        elif command == "count":
            count = await db.get_table_count(params["table"])
            return {"text": f"📊 *`{params['table']}`* has *{count}* row(s)."}

        elif command == "raw_sql":
            result = await db.execute_raw_sql(params["sql"])
            return {
                "text": f"🔧 *SQL Result*:\n\n```\n{json.dumps(result, indent=2, default=str)}\n```"
            }

        elif command == "clarify":
            return {"text": f"🤔 {explanation}"}

        elif command == "chat":
            return {"text": f"💬 {explanation}"}

        else:
            return {"text": f"❓ Unknown command: `{command}`. Please try again."}

    except Exception as e:
        ctx = f"\n\n_Context: {explanation}_" if explanation else ""
        return {"text": f"❌ *Error* ({command}):\n{e}{ctx}"}


def format_rows(table_name: str, rows: list[dict]) -> str:
    """Format database rows as readable text for Telegram."""
    text = f"📊 *`{table_name}`* — {len(rows)} row(s):\n\n"
    max_rows = 10
    display_rows = rows[:max_rows]

    for row in display_rows:
        entries = "\n".join(
            f"  • `{key}`: {_truncate(val)}"
            for key, val in row.items()
        )
        text += f"──────────────\n{entries}\n"

    if len(rows) > max_rows:
        text += f"\n_...and {len(rows) - max_rows} more row(s). Use limit/offset to paginate._"

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
    """Truncate long values for display."""
    if val is None:
        return "NULL"
    s = json.dumps(val, default=str) if isinstance(val, (dict, list)) else str(val)
    return s[:max_len - 3] + "..." if len(s) > max_len else s


def _build_change_html(event: str, table: str, records) -> str:
    """Build an HTML email body showing what changed in the database."""
    html = f"<h2>🔔 Database Change Alert</h2>"
    html += f"<p><b>Event:</b> {event} &nbsp; | &nbsp; <b>Table:</b> {table}</p>"

    if isinstance(records, list):
        data_list = records
    elif isinstance(records, dict):
        data_list = [records]
    else:
        html += f"<pre>{json.dumps(records, indent=2, default=str)}</pre>"
        return html

    if not data_list:
        html += "<p><i>No record data available.</i></p>"
        return html

    # Build HTML table
    columns = list(data_list[0].keys())
    html += "<table border='1' cellpadding='6' style='border-collapse: collapse; font-family: Arial, sans-serif;'>"
    html += "<tr style='background-color: #f2f2f2;'>"
    for col in columns:
        html += f"<th style='text-align: left; padding: 8px;'>{col}</th>"
    html += "</tr>"
    for row in data_list:
        html += "<tr>"
        for col in columns:
            val = row.get(col, "")
            html += f"<td style='padding: 8px;'>{val}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def _send_change_email_async(event: str, table: str, records):
    """Send a database change email in a background thread (non-blocking)."""
    if not config.MANAGER_EMAIL or not config.SMTP_SERVER:
        return
    try:
        subject = f"Database Alert: {event} on {table}"
        html = _build_change_html(event, table, records)
        # Run in background thread so it doesn't block the bot
        threading.Thread(target=send_change_email, args=(subject, html), daemon=True).start()
    except Exception:
        pass  # Don't let email errors break the bot


async def get_table_list_for_context() -> list[str]:
    """Get current table list to provide context to the AI."""
    try:
        return await db.list_tables()
    except Exception:
        return []
