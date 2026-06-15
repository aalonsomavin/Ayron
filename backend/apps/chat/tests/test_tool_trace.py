import pytest

from apps.chat.models import AgentEvent, Message
from apps.chat.tool_trace import build_trace_summary, tool_trace_for_message


@pytest.mark.django_db
class TestToolTrace:
    def test_tool_trace_from_plan_and_tool_events(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_label": "Buscando datos",
                "tool_subtitle": 'SELECT * FROM "Album" LIMIT 10',
                "tool_call_id": "call_1",
                "input": {"sql": 'SELECT * FROM "Album" LIMIT 10'},
            },
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "show_data_table",
                "tool_label": "Mostrar tabla",
                "tool_subtitle": "10 filas",
                "tool_call_id": "call_2",
                "input": {"rows": [[1]] * 10},
            },
            sequence_number=1,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["summary"] == "Buscó datos 1 vez, mostró 1 tabla"
        assert len(trace["items"]) == 2
        assert trace["items"][0]["label"] == "Buscando datos"
        assert trace["items"][1]["tool"] == "show_data_table"

    def test_tool_trace_returns_none_without_events(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Hola",
        )

        assert tool_trace_for_message(assistant_message) is None

    def test_build_trace_summary_single_item(self):
        items = [{"label": "Listar tablas", "tool": "list_tables"}]
        assert build_trace_summary(items) == "Listar tablas"
