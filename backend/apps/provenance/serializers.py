from apps.provenance.models import DataAccess, DataClaim
from apps.provenance.services import get_tool_start_label, serialize_data_access_detail
from apps.provenance.spreadsheet_access import spreadsheet_source_label


def serialize_integration(integration) -> dict | None:
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


def serialize_data_access(data_access: DataAccess) -> dict:
    detail = serialize_data_access_detail(data_access)
    payload = {key: value for key, value in detail.items() if key != "preview_table"}
    payload["id"] = str(data_access.id)
    payload["executed_at"] = data_access.executed_at.isoformat()
    if data_access.access_kind != DataAccess.AccessKind.SQL:
        payload["request"] = data_access.request or {}
        payload["response_summary"] = data_access.response_summary or {}
    return payload


def serialize_claim(claim: DataClaim) -> dict:
    return {
        "id": str(claim.id),
        "claim_key": claim.claim_key,
        "label": claim.label,
        "definition": claim.definition or {},
        "surface": claim.surface,
        "artifact_version": claim.artifact_version,
    }


def serialize_provenance_link(link) -> dict:
    return {
        "ordinal": link.ordinal,
        "transformation": link.transformation,
        "data_access": serialize_data_access(link.data_access),
    }


def serialize_claim_detail(claim: DataClaim) -> dict:
    links = list(
        claim.provenance_links.select_related("data_access__integration", "data_access__file")
        .order_by("ordinal")
    )
    data_accesses = [serialize_data_access(link.data_access) for link in links]
    source = None
    if links:
        first_access = links[0].data_access
        source = serialize_integration(first_access.integration)
        if source is None:
            source_label = spreadsheet_source_label(first_access)
            if source_label:
                source = {"source_label": source_label}

    payload = {
        "claim": serialize_claim(claim),
        "data_accesses": data_accesses,
        "source": source,
        "provenance_links": [serialize_provenance_link(link) for link in links],
    }
    if len(links) == 1:
        payload["transformation"] = links[0].transformation
    else:
        payload["transformation"] = ""
    return payload
