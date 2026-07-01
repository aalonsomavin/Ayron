import json

import pytest
from django.urls import reverse
from unittest.mock import MagicMock, patch

from apps.chat.models import AgentEvent, Conversation, Message
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provask", password="pass")


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provaskother", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user, title="Provenance ask test")


@pytest.fixture
def data_access(conversation):
    integration = Integration.objects.create(
        slug="mexar-ask-test",
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
        tool_call_id="call_ask_test",
        source_ref="sql_1",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT sku FROM comercial_productos LIMIT 10"},
        response_summary={
            "tables": ["comercial_productos"],
            "columns": ["sku"],
            "row_count": 10,
            "user_summary": "Consulta de productos.",
        },
    )


@pytest.fixture
def claim(conversation, data_access):
    message = conversation.messages.first()
    claim = DataClaim.objects.create(
        conversation=conversation,
        message=message,
        claim_key="chat-chart-ask",
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
    return claim


@pytest.mark.django_db
class TestProvenanceAskSendMessage:
    def test_send_with_claim_context_creates_provenance_ask_event(
        self, client, user, conversation, claim, data_access
    ):
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        context = {
            "open_source": "claim",
            "claim_id": str(claim.id),
            "tool_call_id": data_access.tool_call_id,
            "source_ref": data_access.source_ref,
        }

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-ask-1")
            response = client.post(
                url,
                {
                    "content": "Explícame cómo obtuviste estos datos.",
                    "provenance_context": json.dumps(context),
                },
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 200
        user_message = conversation.messages.filter(role=Message.Role.USER).first()
        event = AgentEvent.objects.get(
            message=user_message,
            event_type=AgentEvent.EventType.PROVENANCE_ASK,
        )
        assert event.payload["claim_id"] == str(claim.id)
        assert event.payload["open_source"] == "claim"

    def test_send_with_tool_trace_context_creates_provenance_ask_event(
        self, client, user, conversation, data_access
    ):
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        context = {
            "open_source": "tool_trace",
            "tool_call_id": data_access.tool_call_id,
            "source_ref": data_access.source_ref,
        }

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-ask-2")
            response = client.post(
                url,
                {
                    "content": "Explícame cómo obtuviste estos datos.",
                    "provenance_context": json.dumps(context),
                },
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 200
        user_message = conversation.messages.filter(role=Message.Role.USER).first()
        event = AgentEvent.objects.get(
            message=user_message,
            event_type=AgentEvent.EventType.PROVENANCE_ASK,
        )
        assert event.payload["open_source"] == "tool_trace"
        assert event.payload["tool_call_id"] == "call_ask_test"

    def test_send_rejects_foreign_claim(self, client, user, other_user, conversation, claim):
        other_conversation = Conversation.objects.create(user=other_user, title="Other")
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        context = {
            "open_source": "claim",
            "claim_id": str(claim.id),
            "tool_call_id": "",
            "source_ref": "",
        }

        claim.conversation = other_conversation
        claim.save(update_fields=["conversation"])

        response = client.post(
            url,
            {
                "content": "Explícame cómo obtuviste estos datos.",
                "provenance_context": json.dumps(context),
            },
        )

        assert response.status_code == 400
        assert not AgentEvent.objects.filter(event_type=AgentEvent.EventType.PROVENANCE_ASK).exists()

    def test_send_rejects_invalid_json(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        response = client.post(
            url,
            {
                "content": "Explícame cómo obtuviste estos datos.",
                "provenance_context": "{not-json",
            },
        )

        assert response.status_code == 400
