from apps.agent.tools.display import PLAN_TOOL_LABEL, get_tool_display
from apps.chat.models import AgentEvent


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


def _trace_items_from_events(events: list[AgentEvent]) -> list[dict]:
    items: list[dict] = []
    for event in events:
        payload = event.payload
        if event.event_type == AgentEvent.EventType.PLAN:
            items.append(
                {
                    "label": payload.get("tool_label") or PLAN_TOOL_LABEL,
                    "detail": _plan_detail(payload.get("todos")),
                    "tool": payload.get("tool") or "write_todos",
                }
            )
            continue

        if event.event_type != AgentEvent.EventType.TOOL_START:
            continue

        tool_name = payload.get("tool", "")
        display = get_tool_display(tool_name, payload.get("input"))
        items.append(
            {
                "label": payload.get("tool_label") or display.get("tool_label") or tool_name,
                "detail": payload.get("tool_subtitle") or display.get("tool_subtitle", ""),
                "tool": tool_name,
            }
        )

    return items


def build_trace_summary(items: list[dict]) -> str:
    if not items:
        return ""

    if len(items) == 1:
        return items[0]["label"]

    counts: dict[str, int] = {}
    for item in items:
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

    known = sum(counts.values())
    unknown = len(items) - known
    if unknown > 0:
        parts.append(f"usó {unknown} {'herramienta' if unknown == 1 else 'herramientas'}")

    if not parts:
        parts.append(
            f"Usó {len(items)} {'herramienta' if len(items) == 1 else 'herramientas'}"
        )

    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def tool_trace_for_message(message) -> dict | None:
    events = list(
        AgentEvent.objects.filter(
            message=message,
            event_type__in=(
                AgentEvent.EventType.PLAN,
                AgentEvent.EventType.TOOL_START,
            ),
        ).order_by("sequence_number")
    )
    items = _trace_items_from_events(events)
    if not items:
        return None

    return {
        "items": items,
        "summary": build_trace_summary(items),
    }
