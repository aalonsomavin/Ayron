import re
from collections.abc import Callable

ToolInput = dict | None
DisplayBuilder = Callable[[ToolInput], dict[str, str]]

SQL_SUBTITLE_MAX_LEN = 80
SQL_TABLE_PATTERN = re.compile(
    r'\b(?:FROM|JOIN)\s+"?([a-zA-Z_][a-zA-Z0-9_]*)"?',
    re.IGNORECASE,
)


def _truncate(text: str, max_len: int = SQL_SUBTITLE_MAX_LEN) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1] + "…"


def _humanize_tool_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("_") if part)


def _text_value(tool_input: ToolInput, *keys: str) -> str:
    if not tool_input:
        return ""
    for key in keys:
        value = tool_input.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _extract_sql_table(sql: str) -> str:
    match = SQL_TABLE_PATTERN.search(sql)
    return match.group(1) if match else ""


def _title_phrase(action: str, title: str, fallback: str) -> str:
    title = title.strip()
    if not title:
        return fallback
    words = title.split()
    first = words[0].lower()
    if first in {"reporte", "informe", "memo", "documento", "análisis", "analisis"}:
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        phrase = f"el {first} {rest}".strip()
        return f"{action} {phrase}"
    if first in {"hoja", "tabla", "planilla"}:
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        phrase = f"la {first} {rest}".strip()
        return f"{action} {phrase}"
    return f"{action} {title[0].lower()}{title[1:]}" if title else fallback


def _document_label(action: str, tool_input: ToolInput) -> str:
    title = _text_value(tool_input, "title", "filename")
    return _title_phrase(action, title, f"{action} un documento")


def _spreadsheet_label(action: str, tool_input: ToolInput) -> str:
    title = _text_value(tool_input, "title", "filename", "name")
    return _title_phrase(action, title, f"{action} una hoja de cálculo")


def _path_basename(tool_input: ToolInput) -> str:
    path = _text_value(tool_input, "file_path", "path", "filename")
    if not path:
        return ""
    normalized = path.replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] if normalized else ""


def _filesystem_label(action: str, tool_input: ToolInput) -> str:
    filename = _path_basename(tool_input)
    if filename:
        return f"{action} {filename}"
    return f"{action} un archivo"


def _read_file_display(tool_input: ToolInput) -> dict[str, str]:
    path = _text_value(tool_input, "file_path", "path", "filename")
    display = {
        "tool_label": _filesystem_label("Leyó", tool_input),
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }
    if path:
        display["tool_subtitle"] = _truncate(path, 60)
    return display


def _write_file_display(tool_input: ToolInput) -> dict[str, str]:
    path = _text_value(tool_input, "file_path", "path", "filename")
    display = {
        "tool_label": _filesystem_label("Escribió", tool_input),
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }
    if path:
        display["tool_subtitle"] = _truncate(path, 60)
    return display


def _edit_file_display(tool_input: ToolInput) -> dict[str, str]:
    path = _text_value(tool_input, "file_path", "path", "filename")
    display = {
        "tool_label": _filesystem_label("Editó", tool_input),
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }
    if path:
        display["tool_subtitle"] = _truncate(path, 60)
    return display


def _grep_display(tool_input: ToolInput) -> dict[str, str]:
    pattern = _text_value(tool_input, "pattern", "query")
    display = {
        "tool_label": "Buscó texto en archivos" if pattern else "Buscó en archivos",
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }
    if pattern:
        display["tool_subtitle"] = _truncate(pattern, 60)
    return display


def _ls_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Listó archivos del workspace",
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }


def _glob_display(tool_input: ToolInput) -> dict[str, str]:
    pattern = _text_value(tool_input, "pattern", "glob_pattern")
    display = {
        "tool_label": "Buscó archivos por patrón",
        "tool_tag": "Archivo",
        "tool_icon": "file",
    }
    if pattern:
        display["tool_subtitle"] = _truncate(pattern, 60)
    return display


def _list_tables_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Revisó tablas disponibles",
        "tool_subtitle": "Mexar Pharma",
        "tool_tag": "Base de datos",
        "tool_icon": "database",
    }


def _describe_table_display(tool_input: ToolInput) -> dict[str, str]:
    table_name = _text_value(tool_input, "table_name")
    label = f"Describió la tabla {table_name}" if table_name else "Describió una tabla"
    display = {
        "tool_label": label,
        "tool_tag": "Base de datos",
        "tool_icon": "database",
    }
    if table_name:
        display["tool_subtitle"] = table_name
    return display


def _run_sql_query_display(tool_input: ToolInput) -> dict[str, str]:
    purpose = _text_value(tool_input, "purpose")
    sql = _text_value(tool_input, "sql")
    table_name = _extract_sql_table(sql) if sql else ""
    if purpose:
        label = _truncate(purpose)
        subtitle = table_name or (_truncate(sql) if sql else "")
    elif table_name:
        label = f"Consultó datos de {table_name}"
        subtitle = _truncate(sql) if sql else ""
    else:
        label = "Consultó datos"
        subtitle = _truncate(sql) if sql else ""
    display = {
        "tool_label": label,
        "tool_tag": "SQL",
        "tool_icon": "terminal",
    }
    if subtitle:
        display["tool_subtitle"] = subtitle
    return display


def _show_data_table_display(tool_input: ToolInput) -> dict[str, str]:
    rows = tool_input.get("rows") if tool_input else None
    count = len(rows) if isinstance(rows, list) else 0
    if count:
        row_word = "fila" if count == 1 else "filas"
        label = f"Mostró tabla con {count} {row_word}"
        subtitle = f"{count} {row_word}"
    else:
        label = "Mostró una tabla de datos"
        subtitle = ""
    display = {
        "tool_label": label,
        "tool_tag": "Datos",
        "tool_icon": "chart",
    }
    if subtitle:
        display["tool_subtitle"] = subtitle
    return display


def _show_chart_display(tool_input: ToolInput) -> dict[str, str]:
    chart_type = str(tool_input.get("chart_type", "")).strip().lower() if tool_input else ""
    labels = tool_input.get("labels") if tool_input else None
    type_labels = {"bar": "barras", "line": "línea", "pie": "torta"}
    type_label = type_labels.get(chart_type, chart_type or "datos")
    count = len(labels) if isinstance(labels, list) else 0
    label = f"Mostró gráfico de {type_label}" if chart_type else "Mostró un gráfico"
    display = {
        "tool_label": label,
        "tool_tag": "Datos",
        "tool_icon": "chart",
    }
    if chart_type and count:
        point_word = "punto" if count == 1 else "puntos"
        display["tool_subtitle"] = f"{type_labels.get(chart_type, chart_type).capitalize()} · {count} {point_word}"
    return display


def _create_document_display(tool_input: ToolInput) -> dict[str, str]:
    filename = _text_value(tool_input, "filename")
    display = {
        "tool_label": _document_label("Creó", tool_input),
        "tool_tag": "Word",
        "tool_icon": "file-doc",
    }
    if filename:
        display["tool_subtitle"] = filename
    return display


def _update_document_display(tool_input: ToolInput) -> dict[str, str]:
    filename = _text_value(tool_input, "filename")
    display = {
        "tool_label": _document_label("Actualizó", tool_input),
        "tool_tag": "Word",
        "tool_icon": "file-doc",
    }
    if filename:
        display["tool_subtitle"] = filename
    return display


def _create_spreadsheet_display(tool_input: ToolInput) -> dict[str, str]:
    filename = _text_value(tool_input, "filename")
    display = {
        "tool_label": _spreadsheet_label("Creó", tool_input),
        "tool_tag": "Excel",
        "tool_icon": "file-sheet",
    }
    if filename:
        display["tool_subtitle"] = filename
    return display


def _update_spreadsheet_display(tool_input: ToolInput) -> dict[str, str]:
    filename = _text_value(tool_input, "filename")
    display = {
        "tool_label": _spreadsheet_label("Actualizó", tool_input),
        "tool_tag": "Excel",
        "tool_icon": "file-sheet",
    }
    if filename:
        display["tool_subtitle"] = filename
    return display


def _get_spreadsheet_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Leyó una hoja de cálculo",
        "tool_tag": "Excel",
        "tool_icon": "file-sheet",
    }


def _list_conversation_files_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Listó documentos de la conversación",
        "tool_tag": "Word",
        "tool_icon": "file-doc",
    }


def _get_document_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Leyó un documento",
        "tool_tag": "Word",
        "tool_icon": "file-doc",
    }


def _hydrate_html_artifact_display(_: ToolInput) -> dict[str, str]:
    return {
        "tool_label": "Cargó artifact al workspace",
        "tool_tag": "HTML",
        "tool_icon": "code",
    }


def _html_artifact_subtitle(tool_input: ToolInput) -> str:
    if not tool_input:
        return "HTML"
    path = str(tool_input.get("path") or "").strip()
    if "ay-dash-page" in path or str(tool_input.get("html_kind") or "") == "dashboard":
        return "Dashboard"
    return "HTML"


def _validate_html_artifact_display(tool_input: ToolInput) -> dict[str, str]:
    subtitle = _html_artifact_subtitle(tool_input)
    return {
        "tool_label": "Validó HTML del workspace",
        "tool_subtitle": subtitle,
        "tool_tag": "HTML",
        "tool_icon": "code",
    }


def _publish_html_artifact_display(tool_input: ToolInput) -> dict[str, str]:
    subtitle = _html_artifact_subtitle(tool_input)
    return {
        "tool_label": "Publicó reporte HTML",
        "tool_subtitle": subtitle,
        "tool_tag": "HTML",
        "tool_icon": "code",
    }


def _ask_clarification_display(tool_input: ToolInput) -> dict[str, str]:
    count = 0
    if tool_input and isinstance(tool_input.get("questions"), list):
        count = len(tool_input["questions"])
    if count:
        label = f"Precisa {count} {'consulta' if count == 1 else 'consultas'}"
    else:
        label = "Precisa consulta"
    return {
        "tool_label": label,
        "tool_tag": "Consulta",
        "tool_icon": "help-circle",
    }


def _write_todos_display(tool_input: ToolInput) -> dict[str, str]:
    todos = tool_input.get("todos") if tool_input else None
    count = len(todos) if isinstance(todos, list) else 0
    if count:
        step_word = "paso" if count == 1 else "pasos"
        label = f"Planificó {count} {step_word}"
    else:
        label = "Planificó los siguientes pasos"
    return {
        "tool_label": label,
        "tool_tag": "Plan",
        "tool_icon": "list-checks",
    }


TOOL_DISPLAY_BUILDERS: dict[str, DisplayBuilder] = {
    "list_tables": _list_tables_display,
    "describe_table": _describe_table_display,
    "run_sql_query": _run_sql_query_display,
    "show_data_table": _show_data_table_display,
    "show_chart": _show_chart_display,
    "create_document": _create_document_display,
    "update_document": _update_document_display,
    "create_spreadsheet": _create_spreadsheet_display,
    "update_spreadsheet": _update_spreadsheet_display,
    "get_spreadsheet": _get_spreadsheet_display,
    "list_conversation_files": _list_conversation_files_display,
    "get_document": _get_document_display,
    "hydrate_html_artifact": _hydrate_html_artifact_display,
    "validate_html_artifact": _validate_html_artifact_display,
    "publish_html_artifact": _publish_html_artifact_display,
    "ask_clarification": _ask_clarification_display,
    "write_todos": _write_todos_display,
    "read_file": _read_file_display,
    "write_file": _write_file_display,
    "edit_file": _edit_file_display,
    "grep": _grep_display,
    "ls": _ls_display,
    "glob": _glob_display,
}

TOOL_TAGS = {name: builder(None).get("tool_tag", "") for name, builder in TOOL_DISPLAY_BUILDERS.items()}
TOOL_ICONS = {name: builder(None).get("tool_icon", "file") for name, builder in TOOL_DISPLAY_BUILDERS.items()}
TOOL_LABELS = {name: builder(None).get("tool_label", _humanize_tool_name(name)) for name, builder in TOOL_DISPLAY_BUILDERS.items()}
PLAN_TOOL_LABEL = TOOL_LABELS["write_todos"]
DONE_TOOL_LABEL = "Listo"
DONE_TOOL_ICON = "check-circle"


def get_tool_display(name: str, tool_input: ToolInput = None) -> dict[str, str]:
    builder = TOOL_DISPLAY_BUILDERS.get(name)
    if builder:
        return builder(tool_input)
    return {
        "tool_label": _humanize_tool_name(name),
        "tool_tag": "Herramienta",
        "tool_icon": "file",
    }


def get_done_display() -> dict[str, str]:
    return {
        "tool_label": DONE_TOOL_LABEL,
        "tool_icon": DONE_TOOL_ICON,
    }
