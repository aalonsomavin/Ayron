import re

from apps.provenance.models import DataAccess

SOURCE_REF_KIND_SQL = "sql"
SOURCE_REF_KIND_CHAT_SHEET = "chat_sheet"
SOURCE_REF_KIND_INTEGRATION_SHEET = "integration_sheet"

SOURCE_REF_PREFIXES = {
    SOURCE_REF_KIND_SQL: "sql",
    SOURCE_REF_KIND_CHAT_SHEET: "chat_sheet",
    SOURCE_REF_KIND_INTEGRATION_SHEET: "integration_sheet",
}

SOURCE_ORIGIN_TO_REF_KIND = {
    "chat_upload": SOURCE_REF_KIND_CHAT_SHEET,
    "integration": SOURCE_REF_KIND_INTEGRATION_SHEET,
}

_SOURCE_REF_PATTERN = re.compile(r"^(sql|chat_sheet|integration_sheet)_\d+$")


def _is_source_ref(identifier: str) -> bool:
    return bool(_SOURCE_REF_PATTERN.match(identifier))


def _source_ref_purpose(data_access: DataAccess) -> str:
    request_data = data_access.request or {}
    response_summary = data_access.response_summary or {}
    purpose = str(request_data.get("purpose") or "").strip()
    if purpose:
        return purpose
    return str(response_summary.get("user_summary") or "").strip()


def _max_index_for_prefix(refs: list[str], prefix: str) -> int:
    max_index = 0
    needle = f"{prefix}_"
    for ref in refs:
        if ref.startswith(needle):
            suffix = ref.removeprefix(needle)
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))
    return max_index


def ref_kind_for_data_access(access_kind: str, response_summary: dict | None) -> str | None:
    if access_kind == DataAccess.AccessKind.SQL:
        return SOURCE_REF_KIND_SQL
    if access_kind == DataAccess.AccessKind.SPREADSHEET:
        source_origin = str((response_summary or {}).get("source_origin") or "").strip()
        return SOURCE_ORIGIN_TO_REF_KIND.get(source_origin)
    return None


def allocate_source_ref(conversation, ref_kind: str) -> str:
    prefix = SOURCE_REF_PREFIXES.get(ref_kind)
    if not prefix:
        raise ValueError(f"Unknown source_ref kind: {ref_kind}")

    refs = list(
        DataAccess.objects.filter(conversation=conversation)
        .exclude(source_ref="")
        .values_list("source_ref", flat=True)
    )
    next_index = _max_index_for_prefix(refs, prefix) + 1
    return f"{prefix}_{next_index}"


def format_available_source_refs(conversation) -> str:
    rows = list(
        DataAccess.objects.filter(conversation=conversation)
        .exclude(source_ref="")
        .order_by("executed_at", "id")
    )
    if not rows:
        return "Ninguna fuente de datos registrada en esta conversación."
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
        .select_related("integration", "file")
        .first()
    )
