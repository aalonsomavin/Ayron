import pytest

from apps.chat.models import AgentEvent, Conversation, Message
from apps.chat.tool_trace import apply_step_visibility, build_trace_summary, tool_trace_for_message


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="traceuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


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
                "tool_label": "Consultó datos de comercial_productos",
                "tool_subtitle": 'SELECT * FROM "Album" LIMIT 10',
                "tool_tag": "SQL",
                "tool_icon": "terminal",
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
                "tool_label": "Mostró tabla con 10 filas",
                "tool_subtitle": "10 filas",
                "tool_tag": "Datos",
                "tool_icon": "chart",
                "tool_call_id": "call_2",
                "input": {"rows": [[1]] * 10},
            },
            sequence_number=1,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.DONE,
            payload={},
            sequence_number=2,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["summary"] == "Buscó datos 1 vez, mostró 1 tabla"
        assert len(trace["items"]) == 3
        assert trace["items"][0]["label"] == "Consultó datos de comercial_productos"
        assert trace["items"][0]["tag"] == "SQL"
        assert trace["items"][0]["icon"] == "terminal"
        assert trace["items"][0]["tool_call_id"] == "call_1"
        assert trace["items"][1]["tool"] == "show_data_table"
        assert trace["items"][2]["label"] == "Listo"
        assert trace["items"][2]["tool"] == "done"

    def test_build_trace_summary_includes_chart(self):
        items = [
            {"label": "Consultó datos", "tool": "run_sql_query"},
            {"label": "Mostró gráfico de línea", "tool": "show_chart"},
        ]
        assert build_trace_summary(items) == "Buscó datos 1 vez, mostró 1 gráfico"

    def test_build_trace_summary_excludes_done_item(self):
        items = [
            {"label": "Consultó datos", "tool": "run_sql_query"},
            {"label": "Listo", "tool": "done"},
        ]
        assert build_trace_summary(items) == "Consultó datos"

    def test_tool_trace_returns_none_without_events(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Hola",
        )

        assert tool_trace_for_message(assistant_message) is None

    def test_build_trace_summary_single_item(self):
        items = [{"label": "Revisó tablas disponibles", "tool": "list_tables"}]
        assert build_trace_summary(items) == "Revisó tablas disponibles"

    def test_apply_step_visibility_marks_overflow(self):
        items = [
            {"label": f"Paso {index}", "tool": f"tool_{index}"}
            for index in range(7)
        ] + [{"label": "Listo", "tool": "done"}]
        hidden = apply_step_visibility(items)
        assert hidden == 2
        assert items[4]["overflow"] is False
        assert items[5]["overflow"] is True
        assert items[6]["overflow"] is True
        assert items[7]["overflow"] is False

    def test_tool_trace_omits_done_when_cancelled(self, conversation):
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
                "tool_call_id": "call_1",
                "input": {"sql": "SELECT 1"},
            },
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.DONE,
            payload={"cancelled": True},
            sequence_number=1,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert len(trace["items"]) == 1
        assert trace["items"][0]["tool"] == "run_sql_query"

    def test_tool_trace_item_includes_tool_call_id(self, conversation):
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
                "tool_call_id": "call_sql_only",
                "input": {"sql": "SELECT 1"},
            },
            sequence_number=0,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["items"][0]["tool_call_id"] == "call_sql_only"

    def test_tool_trace_reconstructs_sql_steps_from_data_access(self, conversation, db):
        from apps.integrations.models import Integration
        from apps.provenance.models import DataAccess

        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        purpose = "Identifico los productos con mayor ingreso vendido."
        integration = Integration.objects.create(
            slug="trace-db",
            name="Trace DB",
            type=Integration.Type.POSTGRES,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_END,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_only_end",
                "success": False,
            },
            sequence_number=0,
        )
        DataAccess.objects.create(
            conversation=conversation,
            message=assistant_message,
            integration=integration,
            tool_call_id="call_only_end",
            access_kind=DataAccess.AccessKind.SQL,
            request={
                "sql": "SELECT producto, SUM(ventas) FROM ventas GROUP BY 1",
                "purpose": purpose,
            },
            response_summary={"row_count": 3},
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["items"][0]["label"] == purpose
        assert trace["items"][0]["tool_call_id"] == "call_only_end"

    def test_tool_trace_uses_tool_end_purpose_when_start_input_is_empty(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        purpose = "Quiero ver ventas por región para comparar desempeño."
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_label": "Consultó datos",
                "tool_call_id": "call_failed",
                "input": {"sql": "DELETE FROM comercial_productos"},
            },
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_END,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_failed",
                "success": False,
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": purpose,
                },
            },
            sequence_number=1,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["items"][0]["label"] == purpose

    def test_tool_trace_uses_purpose_over_stale_tool_label(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        purpose = "Quiero ver ventas por región para comparar desempeño."
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_label": "Consultó datos",
                "tool_subtitle": "DELETE FROM comercial_productos",
                "tool_call_id": "call_failed",
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": purpose,
                },
            },
            sequence_number=0,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert trace["items"][0]["label"] == purpose
        assert trace["items"][0]["detail"] == "comercial_productos"

    def test_tool_trace_omits_tool_call_id_for_non_sql_tools(self, conversation):
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
                "tool": "show_data_table",
                "tool_call_id": "call_table",
                "input": {},
            },
            sequence_number=0,
        )

        trace = tool_trace_for_message(assistant_message)

        assert trace is not None
        assert "tool_call_id" not in trace["items"][0]
