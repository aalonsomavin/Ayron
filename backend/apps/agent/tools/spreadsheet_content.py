import re

from apps.agent.tools.report_content import (
    MAX_TABLE_ROWS,
    normalize_docx_row,
)

MAX_SHEETS = 10
MAX_COLUMNS = 30
INVALID_SHEET_NAME_CHARS = re.compile(r"[\\/*?:\[\]]")


def normalize_xlsx_sheet(sheet: dict) -> dict:
    if not isinstance(sheet, dict):
        raise ValueError("each sheet must be an object")
    name = str(sheet.get("name", "")).strip()
    if not name:
        raise ValueError("each sheet requires a name")
    if len(name) > 31:
        raise ValueError("sheet name exceeds 31 characters")
    if INVALID_SHEET_NAME_CHARS.search(name):
        raise ValueError("sheet name contains invalid characters")
    headers = sheet.get("headers") or []
    rows = sheet.get("rows") or []
    if not headers:
        raise ValueError("sheet requires headers")
    if len(headers) > MAX_COLUMNS:
        raise ValueError(f"sheet columns exceeds maximum of {MAX_COLUMNS}")
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError(f"sheet rows exceeds maximum of {MAX_TABLE_ROWS}")
    normalized_rows = []
    for row in rows:
        normalized = normalize_docx_row(row)
        if normalized is not None:
            normalized_rows.append(normalized)
    return {
        "name": name,
        "headers": [str(h) for h in headers],
        "rows": normalized_rows,
    }


def validate_xlsx_content_json(title: str, sheets: list) -> dict:
    if not title or not str(title).strip():
        raise ValueError("title is required")
    if not isinstance(sheets, list) or not sheets:
        raise ValueError("sheets must be a non-empty list")
    if len(sheets) > MAX_SHEETS:
        raise ValueError(f"sheets exceeds maximum of {MAX_SHEETS}")
    normalized_sheets = [normalize_xlsx_sheet(sheet) for sheet in sheets]
    return {
        "format": "xlsx",
        "title": str(title).strip(),
        "sheets": normalized_sheets,
    }


def revalidate_xlsx_content_json(content_json: dict) -> dict:
    return validate_xlsx_content_json(
        content_json.get("title", ""),
        content_json.get("sheets", []),
    )
