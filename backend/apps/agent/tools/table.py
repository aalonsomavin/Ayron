import json
import re

from langchain_core.tools import tool

AGENT_INSTRUCTION_AFTER_TABLE = (
    "La tabla ya está visible en el chat del usuario. "
    "NO repitas filas, columnas ni valores en tu siguiente mensaje. "
    "No uses listas ni tablas markdown con los mismos datos. "
    "Solo añade una o dos frases de interpretación si aportan contexto, "
    "o termina sin texto."
)
MAX_DISPLAY_ROWS = 25
MAX_DISPLAY_COLS = 12
MAX_CELL_LEN = 200
MAX_CAPTION_LEN = 200
NUMERIC_THRESHOLD = 0.8
NARROW_MAX_LEN = 12
AUTO_MAX_LEN = 18

VALID_COLUMN_WIDTHS = frozenset({"narrow", "auto", "fill"})

EMPTY_CELL = "—"

_ID_HEADER = re.compile(r"\bid\b", re.IGNORECASE)

_NUMERIC_PATTERN = re.compile(
    r"^[\s$€£¥+-]*"
    r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"[\s%]*$"
)


def _normalize_cell(value) -> str:
    if value is None:
        return EMPTY_CELL
    text = str(value).strip()
    if not text:
        return EMPTY_CELL
    if len(text) > MAX_CELL_LEN:
        return text[: MAX_CELL_LEN - 1] + "…"
    return text


def _looks_numeric(text: str) -> bool:
    if text == EMPTY_CELL:
        return False
    return bool(_NUMERIC_PATTERN.match(text))


def detect_numeric_columns(rows: list[list[str]]) -> list[bool]:
    if not rows:
        return []
    col_count = len(rows[0])
    result = []
    for col_idx in range(col_count):
        values = [row[col_idx] for row in rows if col_idx < len(row)]
        non_empty = [v for v in values if v != EMPTY_CELL]
        if not non_empty:
            result.append(False)
            continue
        numeric_count = sum(1 for v in non_empty if _looks_numeric(v))
        result.append(numeric_count / len(non_empty) >= NUMERIC_THRESHOLD)
    return result


def _max_column_content_len(column_label: str, rows: list[list[str]], col_idx: int) -> int:
    lengths = [len(column_label)]
    for row in rows:
        if col_idx < len(row):
            lengths.append(len(row[col_idx]))
    return max(lengths)


def infer_column_widths(
    columns: list[str],
    rows: list[list[str]],
    numeric_columns: list[bool],
) -> list[str]:
    col_count = len(columns)
    widths: list[str] = []

    for col_idx in range(col_count):
        max_len = _max_column_content_len(columns[col_idx], rows, col_idx)
        is_numeric = numeric_columns[col_idx] if col_idx < len(numeric_columns) else False
        is_id = bool(_ID_HEADER.search(columns[col_idx]))

        if is_numeric and (is_id or max_len <= NARROW_MAX_LEN):
            widths.append("narrow")
        elif max_len <= AUTO_MAX_LEN:
            widths.append("auto")
        else:
            widths.append("auto")

    fill_candidates = [
        (col_idx, _max_column_content_len(columns[col_idx], rows, col_idx))
        for col_idx in range(col_count)
        if widths[col_idx] != "narrow"
    ]
    if fill_candidates:
        fill_idx = max(fill_candidates, key=lambda item: item[1])[0]
        widths[fill_idx] = "fill"
    elif col_count:
        widest = max(
            range(col_count),
            key=lambda col_idx: _max_column_content_len(columns[col_idx], rows, col_idx),
        )
        widths[widest] = "fill"

    return widths


def normalize_column_widths(column_widths: list[str] | None, col_count: int) -> list[str] | None:
    if column_widths is None:
        return None
    if len(column_widths) != col_count:
        raise ValueError(f"column_widths must have {col_count} entries, got {len(column_widths)}")

    normalized: list[str] = []
    for width in column_widths:
        key = str(width).strip().lower()
        if key not in VALID_COLUMN_WIDTHS:
            raise ValueError(
                f"Invalid column width '{width}'. Use narrow, auto, or fill."
            )
        normalized.append(key)

    if "fill" not in normalized:
        for idx, width in enumerate(normalized):
            if width == "auto":
                normalized[idx] = "fill"
                break
        else:
            normalized[-1] = "fill"

    return normalized


def resolve_column_widths(
    columns: list[str],
    rows: list[list[str]],
    numeric_columns: list[bool],
    column_widths: list[str] | None = None,
) -> list[str]:
    normalized = normalize_column_widths(column_widths, len(columns))
    if normalized is not None:
        return normalized
    return infer_column_widths(columns, rows, numeric_columns)


def build_grid_template_columns(
    widths: list[str],
    columns: list[str],
    rows: list[list[str]],
) -> str:
    parts = []
    for col_idx, width in enumerate(widths):
        if width == "fill":
            parts.append("minmax(0, 1fr)")
            continue
        max_len = _max_column_content_len(columns[col_idx], rows, col_idx)
        if width == "narrow":
            ch = min(max(max_len, 3), 10)
            parts.append(f"{ch}ch")
        else:
            ch = min(max(max_len, 6), 20)
            parts.append(f"minmax({ch}ch, {min(ch + 2, 24)}ch)")
    return " ".join(parts)


def validate_table_input(
    columns: list[str],
    rows: list[list],
    caption: str = "",
    column_widths: list[str] | None = None,
) -> dict:
    if not columns:
        raise ValueError("At least one column is required")
    if len(columns) > MAX_DISPLAY_COLS:
        raise ValueError(f"Maximum {MAX_DISPLAY_COLS} columns allowed")
    if len(rows) > MAX_DISPLAY_ROWS:
        raise ValueError(f"Maximum {MAX_DISPLAY_ROWS} rows allowed")
    if len(caption) > MAX_CAPTION_LEN:
        raise ValueError(f"Caption must be at most {MAX_CAPTION_LEN} characters")

    normalized_columns = [str(col).strip() for col in columns]
    if any(not col for col in normalized_columns):
        raise ValueError("Column names cannot be empty")

    col_count = len(normalized_columns)
    normalized_rows = []
    for row_idx, row in enumerate(rows):
        if len(row) != col_count:
            raise ValueError(
                f"Row {row_idx + 1} has {len(row)} cells, expected {col_count}"
            )
        normalized_rows.append([_normalize_cell(cell) for cell in row])

    numeric_columns = detect_numeric_columns(normalized_rows)
    widths = resolve_column_widths(
        normalized_columns,
        normalized_rows,
        numeric_columns,
        column_widths,
    )

    return {
        "ok": True,
        "caption": caption.strip(),
        "columns": normalized_columns,
        "rows": normalized_rows,
        "numeric_columns": numeric_columns,
        "column_widths": widths,
        "row_count": len(normalized_rows),
    }


def format_table_payload(payload: dict) -> dict:
    return {
        "caption": payload.get("caption", ""),
        "columns": payload.get("columns", []),
        "rows": payload.get("rows", []),
        "numeric_columns": payload.get("numeric_columns", []),
        "column_widths": payload.get("column_widths", []),
        "row_count": payload.get("row_count", len(payload.get("rows", []))),
    }


def build_agent_tool_response(payload: dict) -> str:
    full = format_table_payload(payload)
    return json.dumps(
        {
            "ok": True,
            "displayed_to_user": True,
            "row_count": full["row_count"],
            "caption": full["caption"],
            "agent_instruction": AGENT_INSTRUCTION_AFTER_TABLE,
        }
    )


def prepare_table_for_render(payload: dict) -> dict:
    table = format_table_payload(payload)
    numeric_columns = table["numeric_columns"]
    if not numeric_columns and table["rows"]:
        numeric_columns = detect_numeric_columns(table["rows"])

    widths = table.get("column_widths") or []
    if not widths and table["columns"]:
        widths = resolve_column_widths(
            table["columns"],
            table["rows"],
            numeric_columns,
        )

    render_rows = []
    for row in table["rows"]:
        render_rows.append(
            [
                {
                    "value": cell,
                    "mono": numeric_columns[col_idx] if col_idx < len(numeric_columns) else False,
                    "width": widths[col_idx] if col_idx < len(widths) else "auto",
                }
                for col_idx, cell in enumerate(row)
            ]
        )
    table["numeric_columns"] = numeric_columns
    table["column_widths"] = widths
    table["grid_template_columns"] = build_grid_template_columns(
        widths,
        table["columns"],
        table["rows"],
    )
    table["render_columns"] = [
        {
            "label": label,
            "mono": numeric_columns[col_idx] if col_idx < len(numeric_columns) else False,
            "width": widths[col_idx] if col_idx < len(widths) else "auto",
        }
        for col_idx, label in enumerate(table["columns"])
    ]
    table["render_rows"] = render_rows
    return table


@tool
def show_data_table(
    columns: list[str],
    rows: list[list[str | int | float | None]],
    caption: str = "",
    column_widths: list[str] | None = None,
) -> str:
    """Display a formatted data table in the chat for the user.

    Use when presenting tabular query results with at most 25 rows and 12 columns.
    The UI renders the table for the user. Your tool response does not need to repeat
    row data — after this call, write at most a brief interpretation or stop.

    Provide human-readable Spanish column headers and pre-formatted cell values
    (currency, percentages, dates). Optional caption for footnotes (e.g. truncated totals).

    Column widths: narrow (IDs), auto (fit content), fill (main text column).
    Example: ["narrow", "fill", "narrow"].
    """
    try:
        payload = validate_table_input(columns, rows, caption, column_widths)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return build_agent_tool_response(payload)
