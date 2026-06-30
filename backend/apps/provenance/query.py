import json

import psycopg

from apps.agent.db import MAX_ROWS, demo_db_connection
from apps.provenance.sql_metadata import columns_from_rows

PREVIEW_ROW_LIMIT = 25


def serialize_preview_rows(rows: list[dict]) -> list[dict]:
    return json.loads(json.dumps(rows[:PREVIEW_ROW_LIMIT], default=str))


def execute_stored_select(sql: str) -> dict:
    from apps.agent.tools.sql import validate_select_only

    query = validate_select_only(sql)
    with demo_db_connection() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(query)
            rows = cur.fetchmany(MAX_ROWS + 1)
            truncated = len(rows) > MAX_ROWS
            if truncated:
                rows = rows[:MAX_ROWS]
    serialized_rows = json.loads(json.dumps(rows, default=str))
    return {
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "truncated": truncated,
        "max_rows": MAX_ROWS,
        "columns": columns_from_rows(serialized_rows),
    }
