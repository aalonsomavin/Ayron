from apps.agent.tools.display import get_tool_display
from apps.agent.tools.table import prepare_table_for_render, validate_table_input
from apps.chat.models import AgentEvent
from apps.integrations.services import get_integration_for_data_access_tool
from apps.provenance.models import DataAccess

RUN_SQL_QUERY_TOOL = "run_sql_query"
FAILED_SQL_STATUS_MESSAGE = "Esta búsqueda no devolvió datos."


def _humanize_name(name: str) -> str:
    return name.replace("_", " ").strip()


def get_data_access_for_tool_call(conversation, tool_call_id: str) -> DataAccess | None:
    if not tool_call_id:
        return None
    return (
        DataAccess.objects.filter(
            conversation=conversation,
            tool_call_id=tool_call_id,
        )
        .select_related("integration")
        .first()
    )


def get_tool_start_label(data_access: DataAccess) -> str:
    event = AgentEvent.objects.filter(
        conversation_id=data_access.conversation_id,
        event_type=AgentEvent.EventType.TOOL_START,
        payload__tool_call_id=data_access.tool_call_id,
    ).first()
    if event is None:
        return ""
    return str(event.payload.get("tool_label") or "")


def _serialize_integration(integration) -> dict | None:
    if integration is None:
        return None
    display = (integration.config or {}).get("display") or {}
    type_label = integration.get_type_display()
    return {
        "name": integration.name,
        "type": integration.type,
        "type_label": type_label,
        "status": display.get("status")
        or ("connected" if integration.is_active else "disconnected"),
        "status_label": display.get("status_label")
        or ("Conectada" if integration.is_active else "Desconectada"),
        "source_label": f"{type_label} · {integration.name}",
    }


def _get_sql_tool_events(conversation, tool_call_id: str) -> tuple[AgentEvent | None, AgentEvent | None]:
    start = AgentEvent.objects.filter(
        conversation=conversation,
        event_type=AgentEvent.EventType.TOOL_START,
        payload__tool_call_id=tool_call_id,
        payload__tool=RUN_SQL_QUERY_TOOL,
    ).first()
    if start is None:
        return None, None
    end = AgentEvent.objects.filter(
        conversation=conversation,
        event_type=AgentEvent.EventType.TOOL_END,
        payload__tool_call_id=tool_call_id,
        payload__tool=RUN_SQL_QUERY_TOOL,
    ).first()
    return start, end


def _resolve_sql_tool_input(start: AgentEvent | None, end: AgentEvent | None) -> dict:
    start_input = (start.payload.get("input") if start else {}) or {}
    end_input = (end.payload.get("input") if end else {}) or {}
    if str(start_input.get("purpose") or "").strip():
        return start_input
    if str(end_input.get("purpose") or "").strip():
        return end_input
    return start_input


def serialize_failed_sql_detail(conversation, tool_call_id: str) -> dict | None:
    start, end = _get_sql_tool_events(conversation, tool_call_id)
    if start is None or end is None:
        return None
    if end.payload.get("success") is not False:
        return None

    tool_input = _resolve_sql_tool_input(start, end)
    purpose = str(tool_input.get("purpose") or "").strip()
    sql = str(tool_input.get("sql") or "").strip()
    display = get_tool_display(RUN_SQL_QUERY_TOOL, tool_input) if purpose else {}
    tool_label = display.get("tool_label") or str(start.payload.get("tool_label") or "").strip()
    narrative = purpose or tool_label

    return {
        "tool_call_id": tool_call_id,
        "sql": sql,
        "tables": [],
        "columns": [],
        "row_count": None,
        "truncated": False,
        "max_rows": None,
        "executed_at": end.created_at,
        "integration": _serialize_integration(
            get_integration_for_data_access_tool(RUN_SQL_QUERY_TOOL)
        ),
        "user_summary": purpose,
        "tool_label": tool_label,
        "narrative": narrative,
        "preview_table": None,
        "has_preview_rows": False,
        "has_sql": bool(sql),
        "failed": True,
        "status_message": FAILED_SQL_STATUS_MESSAGE,
    }


def resolve_provenance_detail(conversation, tool_call_id: str) -> dict | None:
    data_access = get_data_access_for_tool_call(conversation, tool_call_id)
    if data_access is not None:
        detail = serialize_data_access_detail(data_access)
        detail["failed"] = False
        detail["status_message"] = ""
        return detail
    return serialize_failed_sql_detail(conversation, tool_call_id)


def preview_table_from_rows(preview_rows: list[dict]) -> dict | None:
    if not preview_rows:
        return None

    raw_columns = list(preview_rows[0].keys())
    columns = [_humanize_name(column) for column in raw_columns[:12]]
    trimmed_keys = raw_columns[: len(columns)]
    rows = [
        [row.get(key) for key in trimmed_keys]
        for row in preview_rows[:25]
    ]
    try:
        payload = validate_table_input(columns=columns, rows=rows)
    except ValueError:
        return None
    return prepare_table_for_render(payload)


def serialize_data_access_detail(data_access: DataAccess) -> dict:
    integration_data = _serialize_integration(data_access.integration)

    request_data = data_access.request or {}
    response_summary = data_access.response_summary or {}
    preview_rows = response_summary.get("preview_rows") or []
    user_summary = response_summary.get("user_summary") or ""
    tool_label = get_tool_start_label(data_access)

    return {
        "tool_call_id": data_access.tool_call_id,
        "source_ref": data_access.source_ref,
        "sql": request_data.get("sql") or "",
        "tables": response_summary.get("tables") or [],
        "columns": response_summary.get("columns") or [],
        "row_count": response_summary.get("row_count"),
        "truncated": bool(response_summary.get("truncated")),
        "max_rows": response_summary.get("max_rows"),
        "executed_at": data_access.executed_at,
        "integration": integration_data,
        "user_summary": user_summary,
        "tool_label": tool_label,
        "narrative": user_summary or tool_label,
        "preview_table": preview_table_from_rows(preview_rows),
        "has_preview_rows": bool(preview_rows),
        "has_sql": bool(request_data.get("sql")),
    }
