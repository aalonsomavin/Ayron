from collections.abc import Callable

ToolInput = dict | None
SubtitleBuilder = Callable[[ToolInput], str]

SQL_SUBTITLE_MAX_LEN = 80


def _truncate(text: str, max_len: int = SQL_SUBTITLE_MAX_LEN) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1] + "…"


def _humanize_tool_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("_") if part)


def _sql_table_subtitle(tool_input: ToolInput) -> str:
    if not tool_input:
        return ""
    table_name = tool_input.get("table_name")
    return str(table_name).strip() if table_name else ""


def _sql_query_subtitle(tool_input: ToolInput) -> str:
    if not tool_input:
        return ""
    sql = tool_input.get("sql")
    if not sql:
        return ""
    return _truncate(str(sql))


def _table_subtitle(tool_input: ToolInput) -> str:
    if not tool_input:
        return ""
    rows = tool_input.get("rows")
    if isinstance(rows, list) and rows:
        count = len(rows)
        return f"{count} fila" if count == 1 else f"{count} filas"
    return ""


TOOL_DISPLAY: dict[str, tuple[str, SubtitleBuilder | None]] = {
    "list_tables": ("Listar tablas", lambda _: "Base Chinook"),
    "describe_table": ("Describir tabla", _sql_table_subtitle),
    "run_sql_query": ("Buscando datos", _sql_query_subtitle),
    "show_data_table": ("Mostrar tabla", _table_subtitle),
    "write_todos": ("Planificar", None),
}

TOOL_LABELS = {name: label for name, (label, _) in TOOL_DISPLAY.items()}
PLAN_TOOL_LABEL = TOOL_LABELS["write_todos"]


def get_tool_display(name: str, tool_input: ToolInput = None) -> dict[str, str]:
    label, subtitle_builder = TOOL_DISPLAY.get(name, (_humanize_tool_name(name), None))
    display = {"tool_label": label}
    if subtitle_builder:
        subtitle = subtitle_builder(tool_input)
        if subtitle:
            display["tool_subtitle"] = subtitle
    return display
