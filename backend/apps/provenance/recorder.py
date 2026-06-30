from apps.agent.context import get_agent_conversation, get_agent_message
from apps.integrations.services import get_integration_for_data_access_tool
from apps.provenance.models import DataAccess
from apps.provenance.source_refs import allocate_source_ref


def record_data_access(
    *,
    tool_name: str,
    tool_call_id: str,
    access_kind: str,
    request: dict,
    response_summary: dict,
    integration=None,
    file=None,
    agent_event_id=None,
) -> DataAccess | None:
    if not tool_call_id:
        return None

    conversation = get_agent_conversation()
    if conversation is None:
        return None

    if integration is None:
        integration = get_integration_for_data_access_tool(tool_name)

    message = get_agent_message()

    data_access, created = DataAccess.objects.update_or_create(
        conversation=conversation,
        tool_call_id=tool_call_id,
        defaults={
            "message": message,
            "integration": integration,
            "file": file,
            "agent_event_id": agent_event_id,
            "access_kind": access_kind,
            "request": request,
            "response_summary": response_summary,
        },
    )
    if (
        created
        and access_kind == DataAccess.AccessKind.SQL
        and not data_access.source_ref
    ):
        data_access.source_ref = allocate_source_ref(conversation)
        data_access.save(update_fields=["source_ref"])
    return data_access
