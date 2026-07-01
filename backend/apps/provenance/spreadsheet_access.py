PREVIEW_ROW_LIMIT = 25
PREVIEW_COLUMN_LIMIT = 12

SOURCE_ORIGIN_CHAT_UPLOAD = "chat_upload"
SOURCE_ORIGIN_INTEGRATION = "integration"


def _sheet_row_count(sheet: dict) -> int:
    return len(sheet.get("rows") or [])


def _sheet_preview_rows(sheet: dict, *, row_limit: int = PREVIEW_ROW_LIMIT) -> list[dict]:
    headers = sheet.get("headers") or []
    if not headers:
        return []

    trimmed_headers = headers[:PREVIEW_COLUMN_LIMIT]
    preview_rows: list[dict] = []
    for row in (sheet.get("rows") or [])[:row_limit]:
        cells = row.get("cells", []) if isinstance(row, dict) else []
        preview_row: dict = {}
        for col_idx, header in enumerate(trimmed_headers):
            cell = cells[col_idx] if col_idx < len(cells) else {}
            if isinstance(cell, dict):
                preview_row[str(header)] = cell.get("value", "")
            else:
                preview_row[str(header)] = cell
        preview_rows.append(preview_row)
    return preview_rows


def build_spreadsheet_access_summary(file_obj, content_json: dict) -> dict:
    sheets = content_json.get("sheets") or []
    sheet_names = [str(sheet.get("name") or "").strip() for sheet in sheets if sheet.get("name")]
    total_rows = sum(_sheet_row_count(sheet) for sheet in sheets)
    first_sheet = sheets[0] if sheets else {}
    preview_rows = _sheet_preview_rows(first_sheet)
    preview_row_count = len(preview_rows)
    truncated = total_rows > preview_row_count or len(first_sheet.get("headers") or []) > PREVIEW_COLUMN_LIMIT

    return {
        "source_origin": SOURCE_ORIGIN_CHAT_UPLOAD,
        "file_name": file_obj.original_name,
        "file_id": str(file_obj.id),
        "sheets": sheet_names,
        "row_count": total_rows,
        "preview_rows": preview_rows,
        "truncated": truncated,
        "max_rows": PREVIEW_ROW_LIMIT if truncated else None,
        "columns": (first_sheet.get("headers") or [])[:PREVIEW_COLUMN_LIMIT],
    }


def spreadsheet_source_label(data_access) -> str | None:
    response_summary = data_access.response_summary or {}
    source_origin = str(response_summary.get("source_origin") or "").strip()

    if source_origin == SOURCE_ORIGIN_CHAT_UPLOAD:
        file_name = response_summary.get("file_name") or ""
        if not file_name and data_access.file_id:
            file_name = data_access.file.original_name
        if file_name:
            return f"Archivo subido · {file_name}"
        return "Archivo subido"

    if source_origin == SOURCE_ORIGIN_INTEGRATION and data_access.integration_id:
        integration = data_access.integration
        type_label = integration.get_type_display()
        return f"{type_label} · {integration.name}"

    return None
