import json
import re

import psycopg
from langchain_core.tools import tool

from apps.agent.cancellation import check_agent_not_cancelled
from apps.agent.db import MAX_ROWS, demo_db_connection
from apps.agent.tools.errors import build_query_error_response

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
STRING_LITERAL_PATTERN = re.compile(r"'(?:''|[^'])*'")

CHINOOK_TABLES = (
    "Artist",
    "Album",
    "Track",
    "Genre",
    "MediaType",
    "Playlist",
    "PlaylistTrack",
    "Customer",
    "Invoice",
    "InvoiceLine",
    "Employee",
)

CHINOOK_COLUMNS = (
    "ArtistId",
    "AlbumId",
    "TrackId",
    "GenreId",
    "MediaTypeId",
    "PlaylistId",
    "InvoiceId",
    "InvoiceLineId",
    "CustomerId",
    "EmployeeId",
    "SupportRepId",
    "Name",
    "Title",
    "Composer",
    "Milliseconds",
    "Bytes",
    "UnitPrice",
    "Quantity",
    "FirstName",
    "LastName",
    "Company",
    "Address",
    "City",
    "State",
    "Country",
    "PostalCode",
    "Phone",
    "Fax",
    "Email",
    "ReportsTo",
    "BirthDate",
    "HireDate",
    "InvoiceDate",
    "BillingAddress",
    "BillingCity",
    "BillingState",
    "BillingCountry",
    "BillingPostalCode",
    "Total",
)

CHINOOK_IDENTIFIERS = tuple(
    sorted(set(CHINOOK_TABLES + CHINOOK_COLUMNS), key=len, reverse=True)
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


def _quote_identifiers(fragment: str) -> str:
    for identifier in CHINOOK_IDENTIFIERS:
        fragment = re.sub(
            rf'(?<!")\b{re.escape(identifier)}\b(?!")',
            f'"{identifier}"',
            fragment,
            flags=re.IGNORECASE,
        )
    return fragment


def normalize_chinook_sql(sql: str) -> str:
    parts = []
    last = 0
    for match in STRING_LITERAL_PATTERN.finditer(sql):
        parts.append(_quote_identifiers(sql[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_quote_identifiers(sql[last:]))
    return "".join(parts)


def validate_table_name(table_name: str) -> str:
    name = table_name.strip()
    if not TABLE_NAME_PATTERN.match(name):
        raise ValueError("Invalid table name")
    canonical = {table.lower(): table for table in CHINOOK_TABLES}
    return canonical.get(name.lower(), name)


def _rows_to_json(rows: list[dict]) -> str:
    return json.dumps(rows, default=str)


@tool
def list_tables() -> str:
    """List all tables in the public schema of the Chinook demo database."""
    check_agent_not_cancelled()
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    try:
        with demo_db_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query)
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
def run_sql_query(sql: str) -> str:
    """Execute a read-only SELECT query against the Chinook demo database."""
    check_agent_not_cancelled()
    try:
        query = normalize_chinook_sql(validate_select_only(sql))
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
                            'Chinook uses PascalCase identifiers. Example: '
                            'SELECT * FROM "Album" LIMIT 5'
                        ),
                        sql_executed=query,
                    )
                rows = cur.fetchmany(MAX_ROWS + 1)
                truncated = len(rows) > MAX_ROWS
                if truncated:
                    rows = rows[:MAX_ROWS]
    except psycopg.Error as exc:
        return build_query_error_response(str(exc).strip())
    result = {
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "max_rows": MAX_ROWS,
    }
    return _rows_to_json(result)
