import re

from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink
from apps.provenance.source_refs import resolve_source_identifiers

_CLAIM_KEY_PATTERN = re.compile(
    r"""data-ay-claim\s*=\s*(["'])([^"']+)\1""",
    re.IGNORECASE,
)

PROVENANCE_MANIFEST_VERSION = 1


def validate_tool_call_ids(conversation, tool_call_ids: list[str]) -> dict[str, DataAccess]:
    return resolve_source_identifiers(conversation, tool_call_ids)


def extract_claim_keys_from_html(html: str) -> set[str]:
    if not html:
        return set()
    return {match.group(2).strip() for match in _CLAIM_KEY_PATTERN.finditer(html) if match.group(2).strip()}


def _normalize_source_refs(raw_source_refs, raw_tool_call_ids, index: int) -> list[str]:
    source_refs: list[str] = []
    if isinstance(raw_source_refs, list):
        source_refs.extend(str(ref).strip() for ref in raw_source_refs if str(ref).strip())
    if isinstance(raw_tool_call_ids, list):
        source_refs.extend(str(ref).strip() for ref in raw_tool_call_ids if str(ref).strip())
    source_refs = list(dict.fromkeys(source_refs))
    if not source_refs:
        raise ValueError(
            f"provenance[{index}] requiere source_refs (o tool_call_ids) con al menos un valor."
        )
    return source_refs


def _normalize_provenance_item(item: dict, index: int) -> dict:
    if not isinstance(item, dict):
        raise ValueError(f"provenance[{index}] debe ser un objeto.")

    claim_key = str(item.get("claim_key") or "").strip()
    if not claim_key:
        raise ValueError(f"provenance[{index}].claim_key es obligatorio.")

    label = str(item.get("label") or "").strip()
    if not label:
        raise ValueError(f"provenance[{index}].label es obligatorio.")

    source_refs = _normalize_source_refs(item.get("source_refs"), item.get("tool_call_ids"), index)

    definition = item.get("definition")
    if not isinstance(definition, dict):
        raise ValueError(f"provenance[{index}].definition debe ser un objeto.")

    transformation = str(item.get("transformation") or "").strip()

    return {
        "claim_key": claim_key,
        "label": label,
        "source_refs": source_refs,
        "definition": definition,
        "transformation": transformation,
    }


def validate_provenance_payload(conversation, html: str, items: list[dict]) -> list[dict]:
    if not items:
        return []

    normalized_items = [_normalize_provenance_item(item, index) for index, item in enumerate(items)]
    html_keys = extract_claim_keys_from_html(html)

    for item in normalized_items:
        if item["claim_key"] not in html_keys:
            raise ValueError(
                f'claim_key "{item["claim_key"]}" no aparece en el HTML como data-ay-claim.'
            )

    for item in normalized_items:
        resolve_source_identifiers(conversation, item["source_refs"])

    return normalized_items


def _replace_claim_links(
    claim: DataClaim,
    source_refs: list[str],
    data_access_map: dict[str, DataAccess],
    transformation: str,
) -> None:
    ProvenanceLink.objects.filter(claim=claim).delete()
    for ordinal, source_ref in enumerate(source_refs):
        ProvenanceLink.objects.create(
            claim=claim,
            data_access=data_access_map[source_ref],
            transformation=transformation,
            ordinal=ordinal,
        )


def sync_file_claims(
    conversation,
    file_obj,
    message,
    items: list[dict],
    *,
    file_version: int,
) -> dict[str, str]:
    normalized_items = items or []
    claim_keys_in_payload = {item["claim_key"] for item in normalized_items}
    claim_key_map: dict[str, str] = {}

    if normalized_items:
        all_source_refs = [
            source_ref
            for item in normalized_items
            for source_ref in item["source_refs"]
        ]
        data_access_map = resolve_source_identifiers(conversation, all_source_refs)
    else:
        data_access_map = {}

    for item in normalized_items:
        claim, _created = DataClaim.objects.update_or_create(
            artifact_file=file_obj,
            claim_key=item["claim_key"],
            defaults={
                "conversation": conversation,
                "message": message,
                "surface": DataClaim.Surface.DASHBOARD_KPI,
                "label": item["label"],
                "definition": item["definition"],
                "artifact_version": file_version,
            },
        )
        _replace_claim_links(
            claim,
            item["source_refs"],
            data_access_map,
            item["transformation"],
        )
        claim_key_map[item["claim_key"]] = str(claim.id)

    stale_claims = DataClaim.objects.filter(artifact_file=file_obj).exclude(
        claim_key__in=claim_keys_in_payload
    )
    for claim in stale_claims:
        ProvenanceLink.objects.filter(claim=claim).delete()
    stale_claims.delete()

    return claim_key_map


def build_provenance_manifest(claim_key_map: dict[str, str]) -> dict:
    return {
        "version": PROVENANCE_MANIFEST_VERSION,
        "claim_keys": claim_key_map,
    }


def inline_claim_key(surface: str, display_tool_call_id: str) -> str:
    surface_short = surface.removeprefix("chat_")
    return f"chat-{surface_short}-{display_tool_call_id}"


def normalize_inline_source_refs(
    source_refs: list[str] | None,
    tool_call_ids: list[str] | None,
) -> list[str] | None:
    refs: list[str] = []
    if source_refs:
        refs.extend(str(ref).strip() for ref in source_refs if str(ref).strip())
    if tool_call_ids:
        refs.extend(str(ref).strip() for ref in tool_call_ids if str(ref).strip())
    refs = list(dict.fromkeys(refs))
    return refs or None


def create_file_deliverable_claim(
    conversation,
    message,
    file_obj,
    display_tool_call_id: str,
    source_refs: list[str],
    *,
    label: str,
    definition: dict | None = None,
) -> DataClaim:
    data_access_map = resolve_source_identifiers(conversation, source_refs)
    claim_key = f"file-deliverable-{file_obj.id}"

    claim, _created = DataClaim.objects.update_or_create(
        artifact_file=file_obj,
        claim_key=claim_key,
        defaults={
            "conversation": conversation,
            "message": message,
            "surface": DataClaim.Surface.CHAT_FILE,
            "label": label,
            "definition": definition or {},
            "artifact_version": file_obj.version,
        },
    )
    _replace_claim_links(claim, source_refs, data_access_map, "")
    return claim


def claim_id_for_file_deliverable(file_obj) -> str | None:
    provenance = (file_obj.content_json or {}).get("provenance") or {}
    claim_keys = provenance.get("claim_keys") or {}
    deliverable_key = f"file-deliverable-{file_obj.id}"
    claim_id = claim_keys.get(deliverable_key)
    return str(claim_id) if claim_id else None


def create_inline_claim(
    conversation,
    message,
    surface: str,
    display_tool_call_id: str,
    source_refs: list[str],
    *,
    label: str,
    definition: dict | None = None,
) -> DataClaim:
    data_access_map = resolve_source_identifiers(conversation, source_refs)
    claim_key = inline_claim_key(surface, display_tool_call_id)

    claim, _created = DataClaim.objects.update_or_create(
        conversation=conversation,
        message=message,
        claim_key=claim_key,
        artifact_file=None,
        defaults={
            "surface": surface,
            "label": label,
            "definition": definition or {},
            "artifact_version": 1,
        },
    )
    _replace_claim_links(claim, source_refs, data_access_map, "")
    return claim
