import json
import re
from typing import Annotated

import psycopg
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.cancellation import check_agent_not_cancelled
from apps.agent.db import MAX_ROWS, demo_db_connection
from apps.agent.tools.errors import build_query_error_response
from apps.integrations.data_access import DATA_ACCESS_TOOL_SPECS
from apps.provenance.models import DataAccess
from apps.provenance.query import serialize_preview_rows
from apps.provenance.recorder import record_data_access
from apps.provenance.sql_metadata import columns_from_rows, extract_sql_tables

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

DEMO_TABLES = (
    "comercial_areas_terapeuticas",
    "comercial_productos",
    "comercial_instituciones",
    "comercial_pedidos",
    "comercial_pedido_lineas",
    "comercial_inventario",
    "crm_ejecutivos",
    "crm_cuentas",
    "crm_contactos",
    "crm_oportunidades",
    "crm_actividades",
    "competencia_precios",
    "competencia_resumen",
)

FORBIDDEN_KEYWORDS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|"
    r"EXECUTE|CALL|COPY|MERGE|REPLACE|VACUUM|REINDEX|CLUSTER|"
    r"COMMENT|SECURITY|REASSIGN|DISCARD|RESET|LOAD|REFRESH|"
    r"LISTEN|UNLISTEN|NOTIFY|PREPARE|DEALLOCATE|DECLARE|FETCH|MOVE|CLOSE"
    r")\b",
    re.IGNORECASE,
)

RUN_SQL_QUERY_TOOL = "run_sql_query"


def validate_select_only(sql: str) -> str:
    normalized = sql.strip()
    if not normalized:
        raise ValueError("SQL query cannot be empty")

    stripped = normalized.rstrip(";").strip()
    if ";" in stripped:
        raise ValueError("Multiple SQL statements are not allowed")

    if not re.match(r"^\s*SELECT\b", normalized, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")

    if FORBIDDEN_KEYWORDS.search(normalized):
        raise ValueError("Query contains forbidden keywords")

    if re.search(r"\bINTO\b", normalized, re.IGNORECASE):
        raise ValueError("INTO clause is not allowed")

    return normalized


def validate_table_name(table_name: str) -> str:
    name = table_name.strip()
    if not TABLE_NAME_PATTERN.match(name):
        raise ValueError("Invalid table name")
    canonical = {table.lower(): table for table in DEMO_TABLES}
    resolved = canonical.get(name.lower())
    if resolved is None:
        raise ValueError(f"Table '{name}' is not available in the demo database")
    return resolved


def _rows_to_json(rows: list[dict]) -> str:
    return json.dumps(rows, default=str)


def _record_sql_data_access(
    *,
    tool_call_id: str,
    sql: str,
    purpose: str,
    rows: list[dict],
    truncated: bool,
) -> DataAccess | None:
    spec = DATA_ACCESS_TOOL_SPECS.get(RUN_SQL_QUERY_TOOL, {})
    tables = extract_sql_tables(sql)
    columns = columns_from_rows(rows)
    preview_rows = serialize_preview_rows(rows)
    user_summary = purpose.strip()
    return record_data_access(
        tool_name=RUN_SQL_QUERY_TOOL,
        tool_call_id=tool_call_id,
        access_kind=spec.get("kind", "sql"),
        request={"sql": sql, "purpose": user_summary},
        response_summary={
            "tables": tables,
            "columns": columns,
            "row_count": len(rows),
            "truncated": truncated,
            "max_rows": MAX_ROWS,
            "preview_rows": preview_rows,
            "user_summary": user_summary,
        },
    )


@tool
def list_tables() -> str:
    """List all tables in the Mexar Pharma demo database."""
    check_agent_not_cancelled()
    placeholders = ", ".join(["%s"] * len(DEMO_TABLES))
    query = f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND table_name IN ({placeholders})
        ORDER BY table_name
    """
    try:
        with demo_db_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, DEMO_TABLES)
                tables = [row["table_name"] for row in cur.fetchall()]
        return json.dumps(tables)
    except psycopg.Error as exc:
        return build_query_error_response(str(exc).strip())


@tool
def describe_table(table_name: str) -> str:
    """Return columns, types, nullability, defaults, and primary keys for a table."""
    check_agent_not_cancelled()
    try:
        name = validate_table_name(table_name)
    except ValueError as exc:
        return build_query_error_response(str(exc))
    columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
    """
    pk_query = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
    """
    try:
        with demo_db_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(columns_query, (name,))
                columns = cur.fetchall()
                if not columns:
                    return build_query_error_response(f"Table '{name}' not found")
                cur.execute(pk_query, (name,))
                primary_keys = [row["column_name"] for row in cur.fetchall()]
    except psycopg.Error as exc:
        return build_query_error_response(str(exc).strip())
    return json.dumps(
        {
            "table_name": name,
            "columns": columns,
            "primary_keys": primary_keys,
        },
        default=str,
    )


@tool
def run_sql_query(
    sql: str,
    purpose: str,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Execute a read-only SELECT query against the Mexar Pharma demo database.

    purpose: Brief explanation in Spanish (1-2 sentences) for the traceability panel.
    Describe what you are looking for and why, in business language without SQL jargon.
    Do not repeat this explanation in the chat response.
    """
    check_agent_not_cancelled()
    if tool_call_id:
        from apps.agent.context import record_sql_tool_trace_input

        record_sql_tool_trace_input(tool_call_id, sql=sql, purpose=purpose)
    try:
        query = validate_select_only(sql)
    except ValueError as exc:
        return build_query_error_response(str(exc))
    try:
        with demo_db_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                try:
                    cur.execute(query)
                except psycopg.Error as exc:
                    return build_query_error_response(
                        str(exc).strip(),
                        hint=(
                            "Use snake_case table names. Example: "
                            "SELECT * FROM comercial_productos LIMIT 5"
                        ),
                        sql_executed=query,
                    )
                rows = cur.fetchmany(MAX_ROWS + 1)
                truncated = len(rows) > MAX_ROWS
                if truncated:
                    rows = rows[:MAX_ROWS]
    except psycopg.Error as exc:
        return build_query_error_response(str(exc).strip())
    data_access = None
    if tool_call_id:
        data_access = _record_sql_data_access(
            tool_call_id=tool_call_id,
            sql=query,
            purpose=purpose,
            rows=rows,
            truncated=truncated,
        )
    result = {
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "max_rows": MAX_ROWS,
    }
    if data_access and data_access.source_ref:
        result["source_ref"] = data_access.source_ref
    return _rows_to_json(result)
