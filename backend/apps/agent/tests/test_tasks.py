from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from langchain_core.messages import AIMessageChunk, ToolMessage
from openai import OpenAIError

from apps.agent.events import persist_event
from apps.agent.streaming import StreamEventHandler
from apps.agent.tasks import (
    LLM_RETRY_MESSAGE,
    format_agent_error,
    run_agent_conversation,
)
from apps.chat.models import AgentEvent, Conversation, Message

User = get_user_model()


@pytest.fixture
def conversation_with_messages(db):
    user = User.objects.create_user(username="agentuser", password="pass")
    conversation = Conversation.objects.create(user=user, status=Conversation.Status.PROCESSING)
    user_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content="Top 5 artists",
    )
    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="",
    )
    return conversation, user_message, assistant_message


@pytest.mark.django_db
class TestPersistEvent:
    def test_persist_event_sequence_monotonic(self, conversation_with_messages):
        conversation, _, assistant_message = conversation_with_messages

        with patch("apps.agent.events.get_redis_client") as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis

            seq1, event1 = persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.TOKEN,
                payload={"content": "Hello"},
                message=assistant_message,
            )
            seq2, event2 = persist_event(
                conversation=conversation,
                event_type=AgentEvent.EventType.TOKEN,
                payload={"content": " world"},
                message=assistant_message,
            )

        assert seq1 == 0
        assert seq2 == 1
        assert event1.sequence_number == 0
        assert event2.sequence_number == 1
        assert mock_redis.publish.call_count == 2

        first_publish = mock_redis.publish.call_args_list[0]
        assert first_publish.args[0] == f"conversation:{conversation.id}"
        published = __import__("json").loads(first_publish.args[1])
        assert published == {
            "seq": 0,
            "type": AgentEvent.EventType.TOKEN,
            "content": "Hello",
            "message_id": assistant_message.id,
        }


@pytest.mark.django_db
class TestRunAgentConversation:
    def test_run_agent_conversation_persists_stream_and_done(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        stream_chunks = [
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="Top artists: "), {}),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            {
                                "id": "call_1",
                                "name": "list_tables",
                                "args": "{}",
                            }
                        ],
                    ),
                    {},
                ),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(content='["Artist", "Album"]', name="list_tables", tool_call_id="call_1"),
                    {},
                ),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="AC/DC"), {}),
            },
        ]
        mock_agent = MagicMock()
        mock_agent.stream.return_value = stream_chunks

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                run_agent_conversation(
                    str(conversation.id),
                    user_message.id,
                    assistant_message.id,
                )

        assistant_message.refresh_from_db()
        conversation.refresh_from_db()

        assert assistant_message.content == "Top artists: AC/DC"
        assert conversation.status == Conversation.Status.ACTIVE

        event_types = list(
            AgentEvent.objects.filter(conversation=conversation)
            .order_by("sequence_number")
            .values_list("event_type", flat=True)
        )
        assert event_types == [
            AgentEvent.EventType.TOKEN,
            AgentEvent.EventType.TOOL_START,
            AgentEvent.EventType.TOOL_END,
            AgentEvent.EventType.TOKEN,
            AgentEvent.EventType.DONE,
        ]

    def test_run_agent_conversation_marks_failed_on_error(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = RuntimeError("LLM unavailable")

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                with pytest.raises(RuntimeError, match="LLM unavailable"):
                    run_agent_conversation(
                        str(conversation.id),
                        user_message.id,
                        assistant_message.id,
                    )

        conversation.refresh_from_db()
        assert conversation.status == Conversation.Status.FAILED
        assert AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.ERROR,
        ).exists()

    def test_run_agent_conversation_retries_transient_openai_error(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        stream_chunks = [
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="Recovered response"), {}),
            },
        ]
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = [
            OpenAIError("temporary upstream failure"),
            stream_chunks,
        ]

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                with patch("apps.agent.tasks.time.sleep"):
                    run_agent_conversation(
                        str(conversation.id),
                        user_message.id,
                        assistant_message.id,
                    )

        assistant_message.refresh_from_db()
        conversation.refresh_from_db()

        assert assistant_message.content == "Recovered response"
        assert conversation.status == Conversation.Status.ACTIVE
        assert mock_agent.stream.call_count == 2

    def test_run_agent_conversation_emits_friendly_openai_error(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = OpenAIError("upstream failure")

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                with patch("apps.agent.tasks.time.sleep"):
                    with pytest.raises(OpenAIError):
                        run_agent_conversation(
                            str(conversation.id),
                            user_message.id,
                            assistant_message.id,
                        )

        error_event = AgentEvent.objects.get(
            conversation=conversation,
            event_type=AgentEvent.EventType.ERROR,
        )
        assert error_event.payload["message"] == LLM_RETRY_MESSAGE
        assert error_event.payload["recoverable"] is True


@pytest.mark.django_db
class TestFormatAgentError:
    def test_openai_error_uses_retry_message(self):
        assert format_agent_error(OpenAIError("upstream failure")) == LLM_RETRY_MESSAGE

    def test_other_errors_use_string_form(self):
        assert format_agent_error(RuntimeError("boom")) == "boom"


@pytest.mark.django_db
class TestStreamEventHandler:
    def test_write_todos_emits_plan_event(self, conversation_with_messages):
        conversation, _, assistant_message = conversation_with_messages
        emitted = []

        def capture_persist(**kwargs):
            emitted.append(kwargs)
            return len(emitted) - 1, MagicMock()

        handler = StreamEventHandler(
            conversation=conversation,
            message=assistant_message,
            persist_fn=capture_persist,
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            {
                                "id": "call_plan",
                                "name": "write_todos",
                                "args": '{"todos": [{"content": "List tables", "status": "pending"}]}',
                            }
                        ],
                    ),
                    {},
                ),
            }
        )

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == AgentEvent.EventType.PLAN
        assert emitted[0]["payload"]["todos"] == [
            {"content": "List tables", "status": "pending"}
        ]
