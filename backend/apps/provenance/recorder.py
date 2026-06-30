from apps.agent.context import get_agent_conversation, get_agent_message
from apps.integrations.services import get_integration_for_data_access_tool
from apps.provenance.models import DataAccess


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

    data_access, _created = DataAccess.objects.update_or_create(
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
    return data_access
