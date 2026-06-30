import re

SQL_TABLE_PATTERN = re.compile(
    r'\b(?:FROM|JOIN)\s+"?([a-zA-Z_][a-zA-Z0-9_]*)"?',
    re.IGNORECASE,
)


def extract_sql_tables(sql: str) -> list[str]:
    seen_lower: set[str] = set()
    tables: list[str] = []
    for match in SQL_TABLE_PATTERN.finditer(sql):
        name = match.group(1)
        key = name.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        tables.append(name)
    return tables


def columns_from_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return []
    return list(rows[0].keys())
