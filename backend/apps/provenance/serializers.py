from apps.provenance.models import DataAccess, DataClaim
from apps.provenance.services import get_tool_start_label, serialize_data_access_detail


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
    if data_access.access_kind == DataAccess.AccessKind.SQL:
        detail = serialize_data_access_detail(data_access)
        payload = {key: value for key, value in detail.items() if key != "preview_table"}
        payload["id"] = str(data_access.id)
        payload["access_kind"] = data_access.access_kind
        payload["executed_at"] = data_access.executed_at.isoformat()
        return payload

    request_data = data_access.request or {}
    response_summary = data_access.response_summary or {}
    return {
        "id": str(data_access.id),
        "access_kind": data_access.access_kind,
        "tool_call_id": data_access.tool_call_id,
        "source_ref": data_access.source_ref,
        "executed_at": data_access.executed_at.isoformat(),
        "integration": serialize_integration(data_access.integration),
        "request": request_data,
        "response_summary": response_summary,
        "user_summary": response_summary.get("user_summary") or "",
        "tool_label": get_tool_start_label(data_access),
    }


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
        claim.provenance_links.select_related("data_access__integration")
        .order_by("ordinal")
    )
    data_accesses = [serialize_data_access(link.data_access) for link in links]
    source = None
    if links:
        source = serialize_integration(links[0].data_access.integration)

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
