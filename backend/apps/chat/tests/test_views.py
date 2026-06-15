from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.agent.events import persist_event
from apps.chat.models import AgentEvent, Conversation, Message
from apps.chat.views import _content_blocks_for_message, serialize_agent_event

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="chatuser", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.mark.django_db
class TestConversationAccess:
    def test_anonymous_redirected(self, client, conversation):
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_other_user_gets_404(self, client, other_user, conversation):
        client.force_login(other_user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestSendMessage:
    def test_send_message_enqueues_celery(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")
            response = client.post(
                url,
                {"content": "Top 5 artists by albums"},
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 204
        conversation.refresh_from_db()
        assert conversation.status == Conversation.Status.PROCESSING
        assert conversation.celery_task_id == "task-123"
        assert conversation.title == "Top 5 artists by albums"

        messages = list(conversation.messages.order_by("created_at"))
        assert len(messages) == 2
        assert messages[0].role == Message.Role.USER
        assert messages[0].content == "Top 5 artists by albums"
        assert messages[1].role == Message.Role.ASSISTANT
        assert messages[1].content == ""

        mock_task.delay.assert_called_once_with(
            str(conversation.id),
            messages[0].id,
            messages[1].id,
        )

    def test_send_rejects_empty_content(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"content": "   "})
        assert response.status_code == 400

    def test_send_rejects_while_processing(self, client, user, conversation):
        conversation.status = Conversation.Status.PROCESSING
        conversation.save()
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"content": "Another question"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestEventsReplay:
    def test_events_replay_returns_all(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )

        with patch("apps.agent.events.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = MagicMock()
            persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.TOKEN,
                payload={"content": "Hello"},
                message=assistant_message,
            )
            persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.DONE,
                payload={},
                message=assistant_message,
            )

        client.force_login(user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()

        assert data["last_sequence"] == 1
        assert data["status"] == conversation.status
        assert data["has_more"] is False
        assert len(data["events"]) == 2
        assert data["events"][0] == {
            "seq": 0,
            "type": AgentEvent.EventType.TOKEN,
            "content": "Hello",
            "message_id": assistant_message.id,
        }
        assert data["events"][1] == {
            "seq": 1,
            "type": AgentEvent.EventType.DONE,
            "message_id": assistant_message.id,
        }

    def test_events_replay_after_filters(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )

        with patch("apps.agent.events.get_redis_client") as mock_get_redis:
            mock_get_redis.return_value = MagicMock()
            persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.TOKEN,
                payload={"content": "A"},
                message=assistant_message,
            )
            persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.TOKEN,
                payload={"content": "B"},
                message=assistant_message,
            )

        client.force_login(user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"after": "0"})
        data = response.json()

        assert len(data["events"]) == 1
        assert data["events"][0]["seq"] == 1
        assert data["events"][0]["content"] == "B"

    def test_events_replay_localizes_stale_tool_labels(self, client, user, conversation):
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
                "tool": "list_tables",
                "tool_label": "List tables",
                "tool_subtitle": "Chinook database",
                "tool_call_id": "call_1",
                "input": {},
            },
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        data = response.json()

        assert data["events"][0]["tool_label"] == "Listar tablas"
        assert data["events"][0]["tool_subtitle"] == "Base Chinook"

    def test_serialize_agent_event_localizes_tool_events(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        event = AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_label": "Run query",
                "input": {"sql": 'SELECT * FROM "Artist" LIMIT 5'},
                "tool_call_id": "call_2",
            },
            sequence_number=0,
        )

        data = serialize_agent_event(event)

        assert data["tool_label"] == "Buscando datos"
        assert data["tool_subtitle"] == 'SELECT * FROM "Artist" LIMIT 5'

    def test_events_other_user_gets_404(self, client, other_user, conversation):
        client.force_login(other_user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestConversationDetail:
    def test_detail_does_not_render_messages_as_alerts(self, client, user, conversation):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hola",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Hola, ¿en qué te ayudo?",
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "user @" not in content
        assert "assistant @" not in content
        assert "Hola, ¿en qué te ayudo?" in content

    def test_detail_renders_table_events(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Aquí están los resultados:",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TABLE,
            payload={
                "caption": "Top 3",
                "columns": ["Artist", "Revenue"],
                "rows": [["AC/DC", "$50.00"]],
                "numeric_columns": [False, True],
                "row_count": 1,
            },
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "AC/DC" in content
        assert "ay-data-table" in content
        assert "Top artists" not in content
        assert "Aquí están los resultados:" in content

    def test_content_blocks_interleave_text_and_table(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Antes Después",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Antes "},
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TABLE,
            payload={
                "columns": ["Artist"],
                "rows": [["AC/DC"]],
                "numeric_columns": [False],
                "row_count": 1,
            },
            sequence_number=1,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Después"},
            sequence_number=2,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert [block["type"] for block in blocks] == ["text", "table", "text"]
        assert blocks[0]["content"] == "Antes "
        assert blocks[1]["table"]["columns"] == ["Artist"]
        assert blocks[2]["content"] == "Después"

    def test_content_blocks_interleave_text_and_chart(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Antes "},
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CHART,
            payload={
                "chart_type": "bar",
                "title": "Por región",
                "labels": ["EMEA"],
                "series": [{"name": "Ingresos", "values": [100]}],
                "value_format": "number",
                "point_count": 1,
            },
            sequence_number=1,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Después"},
            sequence_number=2,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert [block["type"] for block in blocks] == ["text", "chart", "text"]
        assert blocks[1]["chart"]["labels"] == ["EMEA"]
        assert blocks[1]["chart_id"].startswith("chart-")

    def test_detail_renders_chart_events(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Aquí está el gráfico:",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CHART,
            payload={
                "chart_type": "bar",
                "title": "Ingresos por región",
                "labels": ["EMEA", "APAC"],
                "series": [{"name": "Ingresos", "values": [100, 200]}],
                "value_format": "number",
                "point_count": 2,
            },
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "ay-chart" in content
        assert "Ingresos por región" in content
        assert "chart.umd.min.js" in content
        assert "ayron-chart.js" in content
        assert 'type="application/json"' in content

    def test_detail_renders_blocks_in_event_order(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TABLE,
            payload={
                "columns": ["Artist"],
                "rows": [["AC/DC"]],
                "numeric_columns": [False],
                "row_count": 1,
            },
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Interpretación breve."},
            sequence_number=1,
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        content = response.content.decode()

        table_pos = content.index("ay-data-table")
        text_pos = content.index("Interpretación breve.")
        assert table_pos < text_pos

    def test_detail_renders_persisted_tool_trace(self, client, user, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Son 10 álbumes.",
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
                "input": {},
            },
            sequence_number=1,
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        content = response.content.decode()

        assert "ay-tool-trace" in content
        assert "Buscó datos 1 vez, mostró 1 tabla" in content
        assert "Buscando datos" in content
        assert "Mostrar tabla" in content
        assert content.index("Son 10 álbumes.") < content.index("ay-tool-trace")


@pytest.mark.django_db
class TestConversationNew:
    def test_new_creates_and_redirects(self, client, user):
        client.force_login(user)
        response = client.post(reverse("chat:new"))
        assert response.status_code == 302
        conversation = Conversation.objects.get(user=user)
        assert str(conversation.id) in response.url
