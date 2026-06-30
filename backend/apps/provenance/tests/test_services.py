import pytest

from apps.chat.models import AgentEvent, Conversation, Message
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess
from apps.provenance.services import (
    preview_table_from_rows,
    resolve_provenance_detail,
    serialize_data_access_detail,
    serialize_failed_sql_detail,
)


@pytest.fixture
def data_access(db):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username="serialuser", password="pass")
    conversation = Conversation.objects.create(user=user, title="Serializer test")
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="",
    )
    integration = Integration.objects.create(
        slug="serial-db",
        name="Mexar Pharma — Producción",
        type=Integration.Type.POSTGRES,
    )
    AgentEvent.objects.create(
        conversation=conversation,
        message=message,
        event_type=AgentEvent.EventType.TOOL_START,
        payload={
            "tool": "run_sql_query",
            "tool_call_id": "call_serial",
            "tool_label": "Consultó datos de comercial_productos",
        },
        sequence_number=0,
    )
    return DataAccess.objects.create(
        conversation=conversation,
        message=message,
        integration=integration,
        tool_call_id="call_serial",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT sku, nombre FROM comercial_productos LIMIT 2"},
        response_summary={
            "tables": ["comercial_productos"],
            "columns": ["sku", "nombre"],
            "row_count": 2,
            "truncated": False,
            "user_summary": "Ayron revisó productos para comparar ventas.",
            "preview_rows": [
                {"sku": "A1", "nombre": "Asgen"},
                {"sku": "B2", "nombre": "Kebiras"},
            ],
        },
    )


@pytest.mark.django_db
class TestSerializeDataAccessDetail:
    def test_serializer_includes_preview_table(self, data_access):
        detail = serialize_data_access_detail(data_access)

        assert detail["user_summary"] == "Ayron revisó productos para comparar ventas."
        assert detail["narrative"] == detail["user_summary"]
        assert detail["preview_table"] is not None
        assert detail["preview_table"]["render_rows"]
        assert detail["tool_label"] == "Consultó datos de comercial_productos"

    def test_preview_table_from_rows_returns_renderable_table(self):
        table = preview_table_from_rows(
            [
                {"posicion_competitiva": "Dentro del rango mercado", "ventas_totales": "1200.50"},
                {"posicion_competitiva": "Arriba del máximo mercado", "ventas_totales": "800"},
            ]
        )

        assert table is not None
        assert len(table["render_rows"]) == 2
        assert table["render_columns"][0]["label"] == "posicion competitiva"

    def test_narrative_falls_back_to_tool_label(self, data_access):
        data_access.response_summary = {
            **data_access.response_summary,
            "user_summary": "",
        }
        data_access.save(update_fields=["response_summary"])

        detail = serialize_data_access_detail(data_access)

        assert detail["narrative"] == "Consultó datos de comercial_productos"


@pytest.mark.django_db
class TestSerializeFailedSqlDetail:
    def test_failed_sql_detail_from_agent_events(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="faileduser", password="pass")
        conversation = Conversation.objects.create(user=user, title="Failed SQL")
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=message,
            event_type=AgentEvent.EventType.TOOL_START,
            sequence_number=0,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_fail",
                "tool_label": "Consultó datos",
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": "Quería validar el catálogo.",
                },
            },
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=message,
            event_type=AgentEvent.EventType.TOOL_END,
            sequence_number=1,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_fail",
                "success": False,
                "error": "Only SELECT queries are allowed",
            },
        )

        detail = serialize_failed_sql_detail(conversation, "call_fail")

        assert detail is not None
        assert detail["failed"] is True
        assert detail["status_message"] == "Esta búsqueda no devolvió datos."
        assert detail["narrative"] == "Quería validar el catálogo."
        assert detail["preview_table"] is None

    def test_failed_sql_detail_uses_tool_end_purpose(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="failedend", password="pass")
        conversation = Conversation.objects.create(user=user, title="Failed SQL end")
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        purpose = "Quería validar el catálogo comercial."
        AgentEvent.objects.create(
            conversation=conversation,
            message=message,
            event_type=AgentEvent.EventType.TOOL_START,
            sequence_number=0,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_fail_end",
                "tool_label": "Consultó datos",
                "input": {"sql": "DELETE FROM comercial_productos"},
            },
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=message,
            event_type=AgentEvent.EventType.TOOL_END,
            sequence_number=1,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_fail_end",
                "success": False,
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": purpose,
                },
            },
        )

        detail = serialize_failed_sql_detail(conversation, "call_fail_end")

        assert detail is not None
        assert detail["narrative"] == purpose
        assert detail["user_summary"] == purpose

    def test_resolve_prefers_data_access_over_failed_events(self, data_access):
        detail = resolve_provenance_detail(data_access.conversation, "call_serial")

        assert detail is not None
        assert detail["failed"] is False
        assert detail["preview_table"] is not None
