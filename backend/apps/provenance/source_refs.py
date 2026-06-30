import re

from apps.provenance.models import DataAccess

_SOURCE_REF_PATTERN = re.compile(r"^sql_\d+$")


def _is_source_ref(identifier: str) -> bool:
    return bool(_SOURCE_REF_PATTERN.match(identifier))


def _source_ref_purpose(data_access: DataAccess) -> str:
    request_data = data_access.request or {}
    response_summary = data_access.response_summary or {}
    purpose = str(request_data.get("purpose") or "").strip()
    if purpose:
        return purpose
    return str(response_summary.get("user_summary") or "").strip()


def allocate_source_ref(conversation) -> str:
    refs = DataAccess.objects.filter(
        conversation=conversation,
        access_kind=DataAccess.AccessKind.SQL,
    ).exclude(source_ref="").values_list("source_ref", flat=True)
    max_index = 0
    for ref in refs:
        match = _SOURCE_REF_PATTERN.match(ref)
        if match:
            max_index = max(max_index, int(ref.removeprefix("sql_")))
    return f"sql_{max_index + 1}"


def format_available_source_refs(conversation) -> str:
    rows = list(
        DataAccess.objects.filter(
            conversation=conversation,
            access_kind=DataAccess.AccessKind.SQL,
        )
        .exclude(source_ref="")
        .order_by("executed_at", "id")
    )
    if not rows:
        return "Ninguna consulta SQL exitosa registrada en esta conversación."
    parts = []
    for row in rows:
        purpose = _source_ref_purpose(row)
        if purpose:
            parts.append(f"{row.source_ref} ({purpose})")
        else:
            parts.append(row.source_ref)
    return ", ".join(parts)


def resolve_source_identifiers(conversation, identifiers: list[str]) -> dict[str, DataAccess]:
    normalized = [str(identifier).strip() for identifier in identifiers if str(identifier).strip()]
    if not normalized:
        raise ValueError("source_refs no puede estar vacío.")

    unique_identifiers = list(dict.fromkeys(normalized))
    source_refs = [identifier for identifier in unique_identifiers if _is_source_ref(identifier)]
    tool_call_ids = [identifier for identifier in unique_identifiers if not _is_source_ref(identifier)]

    found: dict[str, DataAccess] = {}

    if source_refs:
        for row in DataAccess.objects.filter(
            conversation=conversation,
            source_ref__in=source_refs,
        ):
            found[row.source_ref] = row

    if tool_call_ids:
        for row in DataAccess.objects.filter(
            conversation=conversation,
            tool_call_id__in=tool_call_ids,
        ):
            found[row.tool_call_id] = row

    missing = [identifier for identifier in unique_identifiers if identifier not in found]
    if missing:
        joined = ", ".join(missing)
        available = format_available_source_refs(conversation)
        raise ValueError(
            f"source_ref desconocido en esta conversación: {joined}. "
            f"Disponibles en esta conversación: {available}."
        )
    return found


def get_data_access_for_source_ref(conversation, source_ref: str) -> DataAccess | None:
    if not source_ref:
        return None
    return (
        DataAccess.objects.filter(
            conversation=conversation,
            source_ref=source_ref,
        )
        .select_related("integration")
        .first()
    )
