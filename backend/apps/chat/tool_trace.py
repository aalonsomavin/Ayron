from apps.agent.tools.display import PLAN_TOOL_LABEL, get_done_display, get_tool_display
from apps.chat.models import AgentEvent

VISIBLE_STEP_LIMIT = 5


def _plan_detail(todos) -> str:
    if not isinstance(todos, list):
        return ""
    parts = []
    for item in todos:
        if isinstance(item, dict):
            parts.append(str(item.get("content") or item))
        else:
            parts.append(str(item))
    return ", ".join(parts)


def _message_was_cancelled(message) -> bool:
    return AgentEvent.objects.filter(
        message=message,
        event_type=AgentEvent.EventType.DONE,
        payload__cancelled=True,
    ).exists()


def _trace_item_from_display(
    tool_name: str,
    payload: dict,
    *,
    tool_input=None,
) -> dict:
    resolved_input = tool_input if tool_input is not None else payload.get("input")
    display = get_tool_display(tool_name, resolved_input)
    purpose = ""
    if isinstance(resolved_input, dict):
        purpose = str(resolved_input.get("purpose") or "").strip()
    if tool_name == "run_sql_query" and purpose:
        label = display.get("tool_label") or tool_name
        detail = display.get("tool_subtitle", "")
    else:
        label = payload.get("tool_label") or display.get("tool_label") or tool_name
        detail = payload.get("tool_subtitle") or display.get("tool_subtitle", "")
    item = {
        "label": label,
        "detail": detail,
        "tool": tool_name,
        "tag": payload.get("tool_tag") or display.get("tool_tag", ""),
        "icon": payload.get("tool_icon") or display.get("tool_icon", "file"),
    }
    if tool_name == "run_sql_query":
        tool_call_id = payload.get("tool_call_id")
        if tool_call_id:
            item["tool_call_id"] = tool_call_id
    return item


def _trace_items_from_events(events: list[AgentEvent], *, conversation=None) -> list[dict]:
    sql_end_inputs: dict[str, dict] = {}
    sql_end_payloads: dict[str, dict] = {}
    for event in events:
        if event.event_type != AgentEvent.EventType.TOOL_END:
            continue
        payload = event.payload
        if payload.get("tool") != "run_sql_query":
            continue
        tool_call_id = payload.get("tool_call_id")
        tool_input = payload.get("input")
        if tool_call_id and isinstance(tool_input, dict):
            sql_end_inputs[tool_call_id] = tool_input
        if tool_call_id:
            sql_end_payloads[tool_call_id] = payload

    started_sql_ids: set[str] = set()
    items: list[dict] = []
    for event in events:
        payload = event.payload
        if event.event_type == AgentEvent.EventType.PLAN:
            tool_name = payload.get("tool") or "write_todos"
            display = get_tool_display(tool_name, {"todos": payload.get("todos")})
            items.append(
                {
                    "label": payload.get("tool_label") or display.get("tool_label") or PLAN_TOOL_LABEL,
                    "detail": _plan_detail(payload.get("todos")),
                    "tool": tool_name,
                    "tag": payload.get("tool_tag") or display.get("tool_tag", ""),
                    "icon": payload.get("tool_icon") or display.get("tool_icon", "list-checks"),
                }
            )
            continue

        if event.event_type != AgentEvent.EventType.TOOL_START:
            continue

        tool_name = payload.get("tool", "")
        tool_input = payload.get("input")
        if tool_name == "run_sql_query":
            tool_call_id = payload.get("tool_call_id")
            start_purpose = str((tool_input or {}).get("purpose") or "").strip()
            if tool_call_id and not start_purpose:
                tool_input = sql_end_inputs.get(tool_call_id, tool_input)
            if tool_call_id:
                started_sql_ids.add(tool_call_id)
        items.append(_trace_item_from_display(tool_name, payload, tool_input=tool_input))

    if conversation is not None:
        from apps.provenance.models import DataAccess

        for tool_call_id, end_payload in sql_end_payloads.items():
            if tool_call_id in started_sql_ids:
                continue
            tool_input = dict(sql_end_inputs.get(tool_call_id) or {})
            if not str(tool_input.get("purpose") or "").strip():
                data_access = (
                    DataAccess.objects.filter(
                        conversation=conversation,
                        tool_call_id=tool_call_id,
                    )
                    .only("request")
                    .first()
                )
                if data_access is not None:
                    request = data_access.request or {}
                    tool_input = {
                        "sql": request.get("sql") or "",
                        "purpose": request.get("purpose") or "",
                    }
            synthetic_payload = {
                **end_payload,
                "input": tool_input,
            }
            items.append(
                _trace_item_from_display(
                    "run_sql_query",
                    synthetic_payload,
                    tool_input=tool_input,
                )
            )

    return items


def build_trace_summary(items: list[dict]) -> str:
    if not items:
        return ""

    actionable_items = [item for item in items if item.get("tool") != "done"]
    if not actionable_items:
        return ""

    if len(actionable_items) == 1:
        return actionable_items[0]["label"]

    counts: dict[str, int] = {}
    for item in actionable_items:
        tool = item.get("tool") or item.get("label") or "unknown"
        counts[tool] = counts.get(tool, 0) + 1

    parts: list[str] = []
    if counts.get("list_tables"):
        parts.append("listó tablas")
    if describe_count := counts.get("describe_table"):
        parts.append(
            f"describió {describe_count} {'tabla' if describe_count == 1 else 'tablas'}"
        )
    if sql_count := counts.get("run_sql_query"):
        parts.append(f"buscó datos {sql_count} {'vez' if sql_count == 1 else ' veces'}")
    if table_count := counts.get("show_data_table"):
        parts.append(f"mostró {table_count} {'tabla' if table_count == 1 else ' tablas'}")
    if chart_count := counts.get("show_chart"):
        parts.append(f"mostró {chart_count} {'gráfico' if chart_count == 1 else ' gráficos'}")
    if counts.get("plan") or counts.get("write_todos"):
        parts.append("planificó pasos")
    if doc_count := counts.get("create_document"):
        parts.append(f"creó {doc_count} {'documento' if doc_count == 1 else 'documentos'}")
    if update_doc_count := counts.get("update_document"):
        parts.append(
            f"actualizó {update_doc_count} {'documento' if update_doc_count == 1 else 'documentos'}"
        )
    if sheet_count := counts.get("create_spreadsheet"):
        parts.append(
            f"creó {sheet_count} {'hoja' if sheet_count == 1 else 'hojas'} de cálculo"
        )
    if html_count := (
        counts.get("publish_html_artifact", 0)
        + counts.get("validate_html_artifact", 0)
        + counts.get("hydrate_html_artifact", 0)
    ):
        parts.append(f"trabajó en {html_count} {'reporte HTML' if html_count == 1 else 'reportes HTML'}")
    if read_count := counts.get("read_file"):
        parts.append(f"leyó {read_count} {'archivo' if read_count == 1 else 'archivos'}")
    if write_count := counts.get("write_file"):
        parts.append(f"escribió {write_count} {'archivo' if write_count == 1 else 'archivos'}")
    if edit_count := counts.get("edit_file"):
        parts.append(f"editó {edit_count} {'archivo' if edit_count == 1 else 'archivos'}")

    known = sum(counts.values())
    unknown = len(actionable_items) - known
    if unknown > 0:
        parts.append(f"usó {unknown} {'herramienta' if unknown == 1 else 'herramientas'}")

    if not parts:
        parts.append(
            f"Usó {len(actionable_items)} {'herramienta' if len(actionable_items) == 1 else 'herramientas'}"
        )

    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def apply_step_visibility(items: list[dict]) -> int:
    visible_count = 0
    for item in items:
        if item.get("tool") == "done":
            item["overflow"] = False
            continue
        item["overflow"] = visible_count >= VISIBLE_STEP_LIMIT
        visible_count += 1
    return max(0, visible_count - VISIBLE_STEP_LIMIT)


def tool_trace_for_message(message) -> dict | None:
    events = list(
        AgentEvent.objects.filter(
            message=message,
            event_type__in=(
                AgentEvent.EventType.PLAN,
                AgentEvent.EventType.TOOL_START,
                AgentEvent.EventType.TOOL_END,
            ),
        ).order_by("sequence_number")
    )
    items = _trace_items_from_events(events, conversation=message.conversation)
    if not items:
        return None

    if not _message_was_cancelled(message):
        done = get_done_display()
        items.append(
            {
                "label": done["tool_label"],
                "detail": "",
                "tool": "done",
                "tag": "",
                "icon": done["tool_icon"],
            }
        )

    hidden_step_count = apply_step_visibility(items)

    return {
        "items": items,
        "summary": build_trace_summary(items),
        "hidden_step_count": hidden_step_count,
        "has_overflow_steps": hidden_step_count > 0,
    }
