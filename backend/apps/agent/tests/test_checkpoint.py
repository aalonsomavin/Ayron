import pytest
from django.contrib.auth import get_user_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from unittest.mock import MagicMock, patch

from apps.agent.checkpoint import (
    agent_config,
    rollback_thread_to_turn,
    setup_checkpointer,
    trim_messages_before_user_turn,
    trim_messages_to_user_turn,
    user_message_turn_index,
)
from apps.chat.models import Conversation, Message

User = get_user_model()


@pytest.mark.django_db
class TestCheckpointHelpers:
    def test_agent_config_uses_conversation_id(self, db):
        user = User.objects.create_user(username="cpuser", password="pass")
        conversation = Conversation.objects.create(user=user)
        config = agent_config(conversation.id)
        assert config == {"configurable": {"thread_id": str(conversation.id)}}

    def test_has_checkpoint_false_when_empty(self, db, memory_checkpointer):
        from apps.agent.checkpoint import has_checkpoint

        user = User.objects.create_user(username="cpuser2", password="pass")
        conversation = Conversation.objects.create(user=user)
        assert has_checkpoint(conversation.id) is False

    def test_setup_checkpointer_is_noop_for_memory_saver(self, memory_checkpointer):
        setup_checkpointer()

    def test_trim_messages_to_user_turn(self):
        messages = [
            HumanMessage(content="first"),
            AIMessage(content="answer one"),
            HumanMessage(content="second"),
            AIMessage(content="partial"),
            ToolMessage(content="{}", tool_call_id="call_1", name="run_sql_query"),
        ]
        trimmed = trim_messages_to_user_turn(messages, 1)
        assert len(trimmed) == 3
        assert isinstance(trimmed[-1], HumanMessage)
        assert trimmed[-1].content == "second"

    def test_trim_messages_before_user_turn(self):
        messages = [
            HumanMessage(content="first"),
            AIMessage(content="answer one"),
            HumanMessage(content="second"),
            AIMessage(content="partial"),
        ]
        trimmed = trim_messages_before_user_turn(messages, 1)
        assert len(trimmed) == 2
        assert trimmed[-1].content == "answer one"

    def test_user_message_turn_index(self, db):
        user = User.objects.create_user(username="cpuser3", password="pass")
        conversation = Conversation.objects.create(user=user)
        first = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="one",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="a1",
        )
        second = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="two",
        )
        assert user_message_turn_index(conversation, first) == 0
        assert user_message_turn_index(conversation, second) == 1


@pytest.mark.django_db
class TestRollbackThreadToTurn:
    def test_rollback_keeps_user_message_on_cancel(self, db):
        user = User.objects.create_user(username="rbuser", password="pass")
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="first",
        )
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="second",
        )

        messages = [
            HumanMessage(content="first"),
            AIMessage(content="done"),
            HumanMessage(content="second"),
            AIMessage(content="partial"),
            ToolMessage(content="{}", tool_call_id="call_1", name="run_sql_query"),
        ]
        trimmed = trim_messages_to_user_turn(messages, user_message_turn_index(conversation, user_message))
        assert len(trimmed) == 3

        mock_agent = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {"messages": messages}
        mock_agent.get_state.return_value = mock_state

        with patch("apps.agent.checkpoint.has_checkpoint", return_value=True):
            rollback_thread_to_turn(
                conversation,
                user_message,
                include_user_message=True,
                agent=mock_agent,
            )

        mock_agent.update_state.assert_called_once_with(
            agent_config(conversation.id),
            {"messages": trimmed},
        )

    def test_rollback_deletes_thread_before_first_user_on_retry(self, db):
        user = User.objects.create_user(username="rbuser2", password="pass")
        conversation = Conversation.objects.create(user=user)
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="retry me",
        )

        mock_agent = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [
                HumanMessage(content="retry me"),
                AIMessage(content="partial"),
            ]
        }
        mock_agent.get_state.return_value = mock_state

        with patch("apps.agent.checkpoint.has_checkpoint", return_value=True):
            with patch("apps.agent.checkpoint.get_checkpointer") as mock_get_cp:
                mock_checkpointer = MagicMock()
                mock_get_cp.return_value = mock_checkpointer
                rollback_thread_to_turn(
                    conversation,
                    user_message,
                    include_user_message=False,
                    agent=mock_agent,
                )

        mock_checkpointer.delete_thread.assert_called_once_with(str(conversation.id))
        mock_agent.update_state.assert_not_called()
