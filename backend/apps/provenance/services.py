import json

from apps.agent.events import persist_event
from apps.agent.tools.display import get_tool_display
from apps.agent.tools.table import prepare_table_for_render, validate_table_input
from apps.chat.models import AgentEvent, Conversation, Message
from apps.integrations.services import get_integration_for_data_access_tool
from apps.provenance.models import DataAccess, DataClaim

RUN_SQL_QUERY_TOOL = "run_sql_query"
FAILED_SQL_STATUS_MESSAGE = "Esta búsqueda no devolvió datos."

SURFACE_LABELS = {
    DataClaim.Surface.CHAT_CHART: "gráfico inline",
    DataClaim.Surface.CHAT_TABLE: "tabla inline",
    DataClaim.Surface.DASHBOARD_KPI: "KPI de dashboard",
}

ELEMENT_TYPE_LABELS = {
    DataClaim.Surface.CHAT_CHART: "gráfico",
    DataClaim.Surface.CHAT_TABLE: "tabla",
}


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
        _attach_provenance_ask_fields(detail, open_source="tool_trace")
        return detail
    detail = serialize_failed_sql_detail(conversation, tool_call_id)
    if detail is not None:
        _attach_provenance_ask_fields(detail, open_source="tool_trace")
    return detail


def resolve_claim_provenance_detail(claim) -> dict | None:
    links = list(
        claim.provenance_links.select_related("data_access__integration")
        .order_by("ordinal")
    )
    link = links[0] if links else None
    if link is None:
        return None

    detail = serialize_data_access_detail(link.data_access)
    detail["failed"] = False
    detail["status_message"] = ""

    narrative = str(detail.get("narrative") or "").strip()
    if not narrative and link.transformation:
        narrative = str(link.transformation).strip()
    if not narrative and claim.label:
        narrative = str(claim.label).strip()
    detail["narrative"] = narrative
    _attach_provenance_ask_fields(detail, open_source="claim", claim=claim)
    return detail


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


def _summarize_sql(sql: str) -> str:
    trimmed = " ".join(str(sql or "").split())
    if len(trimmed) > 200:
        return trimmed[:197] + "..."
    return trimmed


def _build_ask_message(*, claim_label: str = "", claim_surface: str = "", narrative: str = "") -> str:
    if claim_label:
        element = ELEMENT_TYPE_LABELS.get(claim_surface, "elemento")
        return f"Explícame de forma sencilla de dónde salieron los datos del {element} «{claim_label}»."
    if narrative:
        return "Explícame de forma sencilla de dónde salieron los datos de este análisis."
    return "Explícame de forma sencilla de dónde salieron estos datos."


def _attach_provenance_ask_fields(
    detail: dict,
    *,
    open_source: str,
    claim: DataClaim | None = None,
) -> None:
    context = {
        "open_source": open_source,
        "tool_call_id": detail.get("tool_call_id") or "",
        "source_ref": detail.get("source_ref") or "",
    }
    if open_source == "claim" and claim is not None:
        context["claim_id"] = str(claim.id)
        detail["claim_id"] = str(claim.id)
        detail["claim_label"] = claim.label
        detail["claim_surface"] = claim.surface
    detail["provenance_ask_context"] = context
    detail["provenance_ask_context_json"] = json.dumps(context, ensure_ascii=False)
    detail["ask_message"] = _build_ask_message(
        claim_label=str(detail.get("claim_label") or ""),
        claim_surface=str(detail.get("claim_surface") or ""),
        narrative=str(detail.get("narrative") or ""),
    )


def _tool_call_exists_in_conversation(conversation: Conversation, tool_call_id: str) -> bool:
    if get_data_access_for_tool_call(conversation, tool_call_id) is not None:
        return True
    return serialize_failed_sql_detail(conversation, tool_call_id) is not None


def parse_provenance_ask_context(raw: str, conversation: Conversation) -> dict:
    if not str(raw or "").strip():
        raise ValueError("provenance_context is required.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid provenance_context JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("provenance_context must be a JSON object.")

    open_source = str(data.get("open_source") or "").strip()
    if open_source not in {"claim", "tool_trace"}:
        raise ValueError("Invalid open_source in provenance_context.")

    tool_call_id = str(data.get("tool_call_id") or "").strip()
    source_ref = str(data.get("source_ref") or "").strip()
    claim_id = str(data.get("claim_id") or "").strip()

    if open_source == "claim":
        if not claim_id:
            raise ValueError("claim_id is required for claim provenance_context.")
        if not DataClaim.objects.filter(id=claim_id, conversation=conversation).exists():
            raise ValueError("claim_id does not belong to this conversation.")
        if tool_call_id and not DataAccess.objects.filter(
            conversation=conversation,
            tool_call_id=tool_call_id,
        ).exists():
            raise ValueError("tool_call_id does not belong to this conversation.")
        return {
            "open_source": "claim",
            "claim_id": claim_id,
            "tool_call_id": tool_call_id,
            "source_ref": source_ref,
        }

    if not tool_call_id:
        raise ValueError("tool_call_id is required for tool_trace provenance_context.")
    if not _tool_call_exists_in_conversation(conversation, tool_call_id):
        raise ValueError("tool_call_id does not belong to this conversation.")
    return {
        "open_source": "tool_trace",
        "tool_call_id": tool_call_id,
        "source_ref": source_ref,
    }


def user_message_has_provenance_ask(user_message: Message | None) -> bool:
    if user_message is None:
        return False
    return AgentEvent.objects.filter(
        message=user_message,
        event_type=AgentEvent.EventType.PROVENANCE_ASK,
    ).exists()


def record_provenance_ask_event(user_message: Message, context: dict) -> None:
    persist_event(
        conversation=user_message.conversation,
        event_type=AgentEvent.EventType.PROVENANCE_ASK,
        payload=context,
        message=user_message,
    )


def _format_data_access_lines(data_access: DataAccess, transformation: str = "") -> list[str]:
    response_summary = data_access.response_summary or {}
    request_data = data_access.request or {}
    tables = response_summary.get("tables") or []
    purpose = str(response_summary.get("user_summary") or "").strip() or get_tool_start_label(data_access)
    tool_call_id = data_access.tool_call_id
    source_ref = data_access.source_ref

    header = f"tool_call_id: {tool_call_id}"
    if source_ref:
        header = f"{header} ({source_ref})"
    parts = [header]
    integration_data = _serialize_integration(getattr(data_access, "integration", None))
    if integration_data:
        parts.append(f"integración: {integration_data['source_label']}")
    if tables:
        parts.append(f"tablas: {', '.join(tables)}")
    if purpose:
        parts.append(f"propósito: {purpose}")

    lines = [f"- {' · '.join(parts)}"]
    if transformation:
        lines.append(f"- transformación: {transformation}")
    sql = str(request_data.get("sql") or "").strip()
    if sql:
        lines.append(f"- SQL (resumen): {_summarize_sql(sql)}")
    return lines


def format_provenance_ask_block(user_message: Message | None) -> str:
    if user_message is None:
        return ""

    event = AgentEvent.objects.filter(
        message=user_message,
        event_type=AgentEvent.EventType.PROVENANCE_ASK,
    ).first()
    if event is None:
        return ""

    context = event.payload or {}
    conversation = user_message.conversation
    lines = [
        "## Solicitud de explicación de procedencia",
        "",
        'El usuario abrió "Origen de los datos" y pidió que expliques cómo se obtuvieron los datos.',
        "",
    ]

    open_source = context.get("open_source")
    if open_source == "claim":
        claim_id = str(context.get("claim_id") or "").strip()
        claim = DataClaim.objects.filter(id=claim_id, conversation=conversation).first()
        lines.extend(["### Elemento visual"])
        if claim is None:
            lines.append(f"- claim_id: {claim_id} (no encontrado)")
        else:
            surface_label = SURFACE_LABELS.get(claim.surface, claim.surface)
            lines.extend(
                [
                    f"- Tipo: {surface_label}",
                    f"- Etiqueta: {claim.label}",
                ]
            )
        lines.extend(["", "### Procedencia consultada", f"- claim_id: {claim_id}"])

        if claim is not None:
            links = list(
                claim.provenance_links.select_related("data_access__integration").order_by("ordinal")
            )
            source_refs = []
            for link in links:
                ref = str(link.data_access.source_ref or "").strip()
                if ref and ref not in source_refs:
                    source_refs.append(ref)
            if source_refs:
                lines.append(f"- source_refs: {', '.join(source_refs)}")
            lines.append("")
            for link in links:
                lines.extend(_format_data_access_lines(link.data_access, link.transformation))
        else:
            lines.append("")
    else:
        tool_call_id = str(context.get("tool_call_id") or "").strip()
        source_ref = str(context.get("source_ref") or "").strip()
        lines.extend(
            [
                "### Elemento visual",
                "- Tipo: consulta SQL del tool trace",
                "",
                "### Procedencia consultada",
            ]
        )
        if source_ref:
            lines.append(f"- source_ref: {source_ref}")
        lines.append(f"- tool_call_id: {tool_call_id}")
        lines.append("")

        data_access = get_data_access_for_tool_call(conversation, tool_call_id)
        if data_access is not None:
            lines.extend(_format_data_access_lines(data_access))
        else:
            failed = serialize_failed_sql_detail(conversation, tool_call_id)
            if failed is not None:
                narrative = str(failed.get("narrative") or failed.get("user_summary") or "").strip()
                if narrative:
                    lines.append(f"- propósito: {narrative}")
                sql = str(failed.get("sql") or "").strip()
                if sql:
                    lines.append(f"- consulta (fallida): {_summarize_sql(sql)}")

    lines.extend(
        [
            "",
            "### Cómo responder",
            "",
            "Usa la procedencia técnica de arriba solo como referencia interna para construir el diagrama.",
            "",
            "Debes invocar `show_origin_diagram` **antes** de escribir texto.",
            "",
            "**Nodos `sources` = integraciones**, no tablas ni consultas sueltas. Cada source es una "
            "conexión de datos distinta (p. ej. PostgreSQL · Mexar Pharma, hoja de cálculo, archivo CSV). "
            "Si todo sale de la misma integración, usa `chain` con una sola source; si intervinieron "
            "2 integraciones → `converge`; 3–4 → `multi_source`.",
            "",
            "En labels visibles usa lenguaje de negocio. Detalla tablas, uniones, filtros, SUM/COUNT u "
            "otras operaciones donde corresponda:",
            "- en `merge` cuando cruzas fuentes,",
            "- en `transforms` cuando hay pasos en cadena,",
            "- en `detail` de cualquier nodo (el usuario puede hacer clic para ampliar).",
            "",
            "Iconos: `database` para PostgreSQL/SQL, `sheet` para Excel/Sheets, `file` para CSV u otros archivos.",
            "",
            "Tras la tool, escribe **una sola frase** de cierre (máx. 25 palabras) en lenguaje de negocio. "
            "No repitas el diagrama ni pegues SQL en el texto.",
            "",
        ]
    )
    return "\n".join(lines)
