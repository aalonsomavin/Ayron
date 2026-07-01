import pytest

from apps.agent.events import persist_event
from apps.chat.models import AgentEvent, Conversation, Message
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink
from apps.provenance.services import format_provenance_ask_block, record_provenance_ask_event


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provservices", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user, title="Provenance services test")


@pytest.fixture
def data_access(conversation):
    integration = Integration.objects.create(
        slug="mexar-services-test",
        name="Mexar Pharma — Producción",
        type=Integration.Type.POSTGRES,
    )
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="",
    )
    return DataAccess.objects.create(
        conversation=conversation,
        message=message,
        integration=integration,
        tool_call_id="call_format_test",
        source_ref="sql_1",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT region, SUM(total) FROM ventas GROUP BY region"},
        response_summary={
            "tables": ["ventas"],
            "columns": ["region", "sum"],
            "row_count": 5,
            "user_summary": "Ventas agregadas por región.",
        },
    )


@pytest.mark.django_db
class TestFormatProvenanceAskBlock:
    def test_claim_context_includes_surface_label_and_source_refs(self, conversation, data_access):
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Explícame los datos.",
        )
        claim = DataClaim.objects.create(
            conversation=conversation,
            message=message,
            claim_key="chat-chart-format",
            surface=DataClaim.Surface.CHAT_CHART,
            label="Ventas por región",
            definition={},
        )
        ProvenanceLink.objects.create(
            claim=claim,
            data_access=data_access,
            transformation="SUM por región",
            ordinal=0,
        )
        record_provenance_ask_event(
            message,
            {
                "open_source": "claim",
                "claim_id": str(claim.id),
                "tool_call_id": data_access.tool_call_id,
                "source_ref": data_access.source_ref,
            },
        )

        block = format_provenance_ask_block(message)

        assert "## Solicitud de explicación de procedencia" in block
        assert "gráfico inline" in block
        assert "Ventas por región" in block
        assert "source_refs: sql_1" in block
        assert "ventas" in block
        assert "SUM por región" in block
        assert "integración:" in block
        assert "### Cómo responder" in block
        assert "show_origin_diagram" in block
        assert "integraciones" in block
        assert "una sola frase" in block
        assert "merge" in block

    def test_tool_trace_context_includes_narrative(self, conversation, data_access):
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Explícame los datos.",
        )
        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.PROVENANCE_ASK,
            payload={
                "open_source": "tool_trace",
                "tool_call_id": data_access.tool_call_id,
                "source_ref": data_access.source_ref,
            },
            message=message,
        )

        block = format_provenance_ask_block(message)

        assert "consulta SQL del tool trace" in block
        assert "call_format_test" in block
        assert "sql_1" in block
        assert "Ventas agregadas por región." in block

    def test_returns_empty_without_event(self, conversation):
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hola",
        )

        assert format_provenance_ask_block(message) == ""
        assert format_provenance_ask_block(None) == ""
