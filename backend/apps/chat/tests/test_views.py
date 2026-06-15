from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.agent.events import persist_event
from apps.chat.models import AgentEvent, Conversation, Message

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

    def test_events_other_user_gets_404(self, client, other_user, conversation):
        client.force_login(other_user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestConversationNew:
    def test_new_creates_and_redirects(self, client, user):
        client.force_login(user)
        response = client.post(reverse("chat:new"))
        assert response.status_code == 302
        conversation = Conversation.objects.get(user=user)
        assert str(conversation.id) in response.url
