"""
Supabase Database Service Layer
Full CRUD operations, schema introspection, and raw SQL execution.
"""

from supabase import create_client, Client
from config import config

# Initialize Supabase client with service_role key (bypasses RLS)
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)


# ─── Table Listing ────────────────────────────────────────────────────

async def list_tables() -> list[str]:
    """List all user-created tables in the public schema."""
    try:
        result = supabase.rpc("get_tables").execute()
        return [row["table_name"] for row in result.data] if result.data else []
    except Exception as e:
        raise Exception(f"Failed to list tables: {e}")


# ─── Schema Introspection ────────────────────────────────────────────

async def get_table_schema(table_name: str) -> list[dict]:
    """Get columns, types, and constraints for a specific table."""
    try:
        result = supabase.rpc("get_table_schema", {"target_table": table_name}).execute()
        return result.data or []
    except Exception as e:
        raise Exception(f"Failed to get schema for '{table_name}': {e}")


# ─── Query / Read ────────────────────────────────────────────────────

async def query_table(
    table_name: str,
    filters: dict = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str = None,
    ascending: bool = True,
) -> list[dict]:
    """Query rows from a table with optional filters, ordering, and pagination."""
    try:
        query = supabase.table(table_name).select("*")

        # Apply filters
        if filters:
            for column, value in filters.items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        if op == "gt":
                            query = query.gt(column, val)
                        elif op == "gte":
                            query = query.gte(column, val)
                        elif op == "lt":
                            query = query.lt(column, val)
                        elif op == "lte":
                            query = query.lte(column, val)
                        elif op == "like":
                            query = query.like(column, val)
                        elif op == "ilike":
                            query = query.ilike(column, val)
                        elif op == "neq":
                            query = query.neq(column, val)
                        elif op == "in":
                            query = query.in_(column, val)
                        else:
                            query = query.eq(column, val)
                else:
                    query = query.eq(column, value)

        if order_by:
            query = query.order(order_by, desc=not ascending)

        query = query.range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or []
    except Exception as e:
        raise Exception(f"Query failed on '{table_name}': {e}")


# ─── Insert ──────────────────────────────────────────────────────────

async def insert_row(table_name: str, row_data: dict) -> list[dict]:
    """Insert one row into a table and return the inserted data."""
    try:
        result = supabase.table(table_name).insert(row_data).execute()
        return result.data or []
    except Exception as e:
        raise Exception(f"Insert failed on '{table_name}': {e}")


# ─── Update ──────────────────────────────────────────────────────────

async def update_row(table_name: str, match: dict, updates: dict) -> list[dict]:
    """Update rows matching conditions and return updated data."""
    try:
        query = supabase.table(table_name).update(updates)
        for column, value in match.items():
            query = query.eq(column, value)
        result = query.execute()
        return result.data or []
    except Exception as e:
        raise Exception(f"Update failed on '{table_name}': {e}")


# ─── Delete ──────────────────────────────────────────────────────────

async def delete_row(table_name: str, match: dict) -> list[dict]:
    """Delete rows matching conditions and return deleted data."""
    try:
        query = supabase.table(table_name).delete()
        for column, value in match.items():
            query = query.eq(column, value)
        result = query.execute()
        return result.data or []
    except Exception as e:
        raise Exception(f"Delete failed on '{table_name}': {e}")


# ─── Raw SQL ─────────────────────────────────────────────────────────

async def execute_raw_sql(sql: str):
    """Execute raw SQL using the execute_sql RPC function."""
    try:
        result = supabase.rpc("execute_sql", {"query_text": sql}).execute()
        return result.data
    except Exception as e:
        raise Exception(f"SQL execution failed: {e}")


# ─── Count ───────────────────────────────────────────────────────────

async def get_table_count(table_name: str) -> int:
    """Get the total row count of a table."""
    try:
        result = supabase.table(table_name).select("*", count="exact").limit(0).execute()
        return result.count or 0
    except Exception as e:
        raise Exception(f"Count failed on '{table_name}': {e}")
