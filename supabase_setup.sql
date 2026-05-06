-- ============================================================
-- Supabase SQL Helper Functions
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- These functions are required for the Telegram bot agent to work.
-- ============================================================

-- 1. List all user tables in the public schema
CREATE OR REPLACE FUNCTION get_tables()
RETURNS TABLE(table_name TEXT) AS $$
BEGIN
  RETURN QUERY
  SELECT t.table_name::TEXT
  FROM information_schema.tables t
  WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
  ORDER BY t.table_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Get schema/columns for a specific table
CREATE OR REPLACE FUNCTION get_table_schema(target_table TEXT)
RETURNS TABLE(
  column_name TEXT,
  data_type TEXT,
  is_nullable TEXT,
  column_default TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.column_name::TEXT,
    c.data_type::TEXT,
    c.is_nullable::TEXT,
    c.column_default::TEXT
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    AND c.table_name = target_table
  ORDER BY c.ordinal_position;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Execute arbitrary SQL (use with caution!)
CREATE OR REPLACE FUNCTION execute_sql(query_text TEXT)
RETURNS JSON AS $$
DECLARE
  result JSON;
BEGIN
  EXECUTE 'SELECT json_agg(row_to_json(t)) FROM (' || query_text || ') t'
  INTO result;
  RETURN COALESCE(result, '[]'::JSON);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
