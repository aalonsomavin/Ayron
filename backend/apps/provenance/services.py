from apps.provenance.models import DataAccess


def get_data_access_for_tool_call(conversation, tool_call_id: str) -> DataAccess | None:
    if not tool_call_id:
        return None
    return DataAccess.objects.filter(
        conversation=conversation,
        tool_call_id=tool_call_id,
    ).first()
