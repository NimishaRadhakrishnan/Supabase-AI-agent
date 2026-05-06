"""
Report Service — Generates AI summaries of the database for managers.
"""

from groq import Groq
from config import config
from services import supabase_service as db
import json

groq_client = Groq(api_key=config.GROQ_API_KEY)

async def generate_manager_report() -> str:
    """Gather overall database stats and ask Groq to format a nice manager report."""
    try:
        # Gather data
        tables = await db.list_tables()
        
        # We will attempt to get some basic summary stats from known tables
        # If the mock tables exist, we can show specific stats. Next step is a generic summary.
        stats = {"tables": tables, "details": {}}
        
        for table in tables:
            count = await db.get_table_count(table)
            stats["details"][table] = {"row_count": count}
            
            # Fetch the first 5 rows to give the AI context of what's inside
            sample = await db.query_table(table, limit=5)
            stats["details"][table]["sample_data"] = sample

        # Generate a prompt for the AI
        prompt = (
            "You are a helpful database management assistant.\n"
            "Below is a JSON dump of the database tables, row counts, and sample data.\n"
            "Please generate a concise, professional, and visually appealing business report.\n"
            "Include emojis.\n"
            "Format the output entirely in Telegram-compatible Markdown (use *bold* instead of **bold**).\n\n"
            f"Database Data:\n{json.dumps(stats, default=str)}"
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=config.GROQ_MODEL,
            temperature=0.3,
            max_tokens=1024,
        )

        report = chat_completion.choices[0].message.content
        return report

    except Exception as e:
        return f"❌ Failed to generate report: {e}"
