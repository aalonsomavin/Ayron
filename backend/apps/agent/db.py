from contextlib import contextmanager

import psycopg
from django.conf import settings

STATEMENT_TIMEOUT_MS = 10_000
MAX_ROWS = 100


def get_demo_db_url() -> str:
    url = settings.DEMO_DB_URL
    if not url:
        raise RuntimeError("DEMO_DB_URL is not configured")
    return url


@contextmanager
def demo_db_connection():
    with psycopg.connect(get_demo_db_url(), connect_timeout=10) as conn:
        conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
        yield conn
