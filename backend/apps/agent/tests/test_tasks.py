import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from openai import OpenAIError

from apps.agent.events import persist_event
from apps.agent.streaming import StreamEventHandler
from apps.agent.tasks import (
    LLM_RETRY_MESSAGE,
    build_stream_input,
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
class TestBuildStreamInput:
    def test_bootstrap_when_no_checkpoint(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        with patch("apps.agent.tasks.has_checkpoint", return_value=False):
            input_state, config = build_stream_input(
                conversation,
                user_message,
                assistant_message.id,
            )
        assert config == {"configurable": {"thread_id": str(conversation.id)}}
        assert input_state["messages"] == [{"role": "user", "content": "Top 5 artists"}]

    def test_incremental_when_checkpoint_exists(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        with patch("apps.agent.tasks.has_checkpoint", return_value=True):
            input_state, config = build_stream_input(
                conversation,
                user_message,
                assistant_message.id,
            )
        assert config == {"configurable": {"thread_id": str(conversation.id)}}
        assert input_state["messages"] == [{"role": "user", "content": "Top 5 artists"}]


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

        with patch("apps.agent.tasks.has_checkpoint", return_value=False):
            with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
                with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                    mock_get_redis.return_value = MagicMock()
                    run_agent_conversation(
                        str(conversation.id),
                        user_message.id,
                        assistant_message.id,
                    )

        mock_agent.stream.assert_called_once()
        stream_args, stream_kwargs = mock_agent.stream.call_args
        assert stream_kwargs["config"] == {"configurable": {"thread_id": str(conversation.id)}}
        assert stream_args[0]["messages"] == [{"role": "user", "content": "Top 5 artists"}]

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

        tool_start = AgentEvent.objects.get(
            conversation=conversation,
            event_type=AgentEvent.EventType.TOOL_START,
        )
        assert tool_start.payload["tool"] == "list_tables"
        assert tool_start.payload["tool_label"] == "Listar tablas"
        assert tool_start.payload["tool_subtitle"] == "YIVTOL · AyronOne"

        tool_end = AgentEvent.objects.get(
            conversation=conversation,
            event_type=AgentEvent.EventType.TOOL_END,
        )
        assert tool_end.payload["tool_label"] == "Listar tablas"

    def test_run_agent_conversation_stops_when_cancelled(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        stream_chunks = [
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="Partial "), {}),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="response"), {}),
            },
        ]
        mock_agent = MagicMock()
        mock_agent.stream.return_value = stream_chunks

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                with patch(
                    "apps.agent.tasks.is_cancelled",
                    side_effect=[False, True],
                ):
                    with patch("apps.agent.tasks.rollback_thread_to_turn") as mock_rollback:
                        run_agent_conversation(
                            str(conversation.id),
                            user_message.id,
                            assistant_message.id,
                        )

        mock_rollback.assert_called_once_with(
            conversation,
            user_message,
            include_user_message=True,
            agent=mock_agent,
        )

        assistant_message.refresh_from_db()
        conversation.refresh_from_db()

        assert assistant_message.content == "Partial response"
        assert conversation.status == Conversation.Status.ACTIVE

        done_event = AgentEvent.objects.get(
            conversation=conversation,
            event_type=AgentEvent.EventType.DONE,
        )
        assert done_event.payload == {"cancelled": True}

    def test_run_agent_conversation_skips_finalize_if_already_stopped(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        conversation.status = Conversation.Status.ACTIVE
        conversation.save()
        mock_agent = MagicMock()
        mock_agent.stream.return_value = [
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="Late token"), {}),
            },
        ]

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                run_agent_conversation(
                    str(conversation.id),
                    user_message.id,
                    assistant_message.id,
                )

        assert not AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.DONE,
        ).exists()

    def test_run_agent_conversation_marks_failed_on_error(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = RuntimeError("LLM unavailable")

        with patch("apps.agent.tasks.create_agent", return_value=mock_agent):
            with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                mock_get_redis.return_value = MagicMock()
                with patch("apps.agent.tasks.rollback_thread_to_turn") as mock_rollback:
                    with pytest.raises(RuntimeError, match="LLM unavailable"):
                        run_agent_conversation(
                            str(conversation.id),
                            user_message.id,
                            assistant_message.id,
                        )

        mock_rollback.assert_called_once_with(
            conversation,
            user_message,
            include_user_message=True,
            agent=mock_agent,
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

    def test_run_agent_conversation_continues_after_tool_error(self, conversation_with_messages):
        conversation, user_message, assistant_message = conversation_with_messages
        error_output = json.dumps(
            {
                "ok": False,
                "error": "Only SELECT queries are allowed",
                "agent_instruction": "retry",
            }
        )
        stream_chunks = [
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            {
                                "id": "call_1",
                                "name": "run_sql_query",
                                "args": '{"sql": "DELETE FROM Artist"}',
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
                    ToolMessage(
                        content=error_output,
                        name="run_sql_query",
                        tool_call_id="call_1",
                    ),
                    {},
                ),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            {
                                "id": "call_2",
                                "name": "run_sql_query",
                                "args": '{"sql": "SELECT 1"}',
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
                    ToolMessage(
                        content='{"rows": [], "row_count": 0, "truncated": false, "max_rows": 100}',
                        name="run_sql_query",
                        tool_call_id="call_2",
                    ),
                    {},
                ),
            },
            {
                "type": "messages",
                "ns": (),
                "data": (AIMessageChunk(content="Consulta corregida."), {}),
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

        assert assistant_message.content == "Consulta corregida."
        assert conversation.status == Conversation.Status.ACTIVE
        tool_end_events = AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.TOOL_END,
        ).order_by("sequence_number")
        assert tool_end_events.count() == 2
        assert tool_end_events[0].payload["success"] is False
        assert "success" not in tool_end_events[1].payload


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
        assert emitted[0]["payload"]["tool_label"] == "Planificar"
        assert emitted[0]["payload"]["todos"] == [
            {"content": "List tables", "status": "pending"}
        ]

    def test_sql_tool_start_includes_display_fields(self, conversation_with_messages):
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
                                "id": "call_sql",
                                "name": "run_sql_query",
                                "args": '{"sql": "SELECT * FROM \\"Artist\\" LIMIT 5"}',
                            }
                        ],
                    ),
                    {},
                ),
            }
        )

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == AgentEvent.EventType.TOOL_START
        assert emitted[0]["payload"]["tool_label"] == "Buscando datos"
        assert emitted[0]["payload"]["tool_subtitle"] == 'SELECT * FROM "Artist" LIMIT 5'

    def test_tool_error_emits_success_false_in_tool_end(self, conversation_with_messages):
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
        error_output = json.dumps(
            {
                "ok": False,
                "error": "Only SELECT queries are allowed",
                "agent_instruction": "retry",
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=error_output,
                        name="run_sql_query",
                        tool_call_id="call_err",
                    ),
                    {},
                ),
            }
        )

        tool_end = emitted[0]
        assert tool_end["event_type"] == AgentEvent.EventType.TOOL_END
        assert tool_end["payload"]["success"] is False
        assert "Only SELECT" in tool_end["payload"]["error"]

    def test_show_data_table_emits_table_event(self, conversation_with_messages):
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
        tool_output = json.dumps(
            {
                "ok": True,
                "caption": "",
                "columns": ["Artist", "Revenue"],
                "rows": [["AC/DC", "$50.00"]],
                "numeric_columns": [False, True],
                "row_count": 1,
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=tool_output,
                        name="show_data_table",
                        tool_call_id="call_table",
                    ),
                    {},
                ),
            }
        )

        assert len(emitted) == 2
        assert emitted[0]["event_type"] == AgentEvent.EventType.TABLE
        assert emitted[0]["payload"]["columns"] == ["Artist", "Revenue"]
        assert emitted[0]["payload"]["render_rows"][0][1]["mono"] is True
        assert emitted[0]["payload"]["tool_call_id"] == "call_table"
        assert emitted[1]["event_type"] == AgentEvent.EventType.TOOL_END
        assert emitted[1]["payload"]["tool"] == "show_data_table"
        assert emitted[1]["payload"]["output_summary"] == "Tabla mostrada"

    def test_show_data_table_uses_staged_tool_input(self, conversation_with_messages):
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
                                "id": "call_table",
                                "name": "show_data_table",
                                "args": json.dumps(
                                    {
                                        "columns": ["Artist"],
                                        "rows": [["AC/DC"]],
                                    }
                                ),
                            }
                        ],
                    ),
                    {},
                ),
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=json.dumps(
                            {
                                "ok": True,
                                "displayed_to_user": True,
                                "row_count": 1,
                                "agent_instruction": "No repitas filas.",
                            }
                        ),
                        name="show_data_table",
                        tool_call_id="call_table",
                    ),
                    {},
                ),
            }
        )

        table_event = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.TABLE
        )
        assert table_event["payload"]["rows"] == [["AC/DC"]]

    def test_show_data_table_stages_after_complete_tool_call(self, conversation_with_messages):
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
                                "id": "call_table",
                                "name": "show_data_table",
                                "args": '{"columns":',
                            }
                        ],
                    ),
                    {},
                ),
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_table",
                                "name": "show_data_table",
                                "args": {
                                    "columns": ["Artist"],
                                    "rows": [["AC/DC"]],
                                },
                            }
                        ],
                    ),
                    {},
                ),
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=json.dumps(
                            {
                                "ok": True,
                                "displayed_to_user": True,
                                "row_count": 1,
                            }
                        ),
                        name="show_data_table",
                        tool_call_id="call_table",
                    ),
                    {},
                ),
            }
        )

        table_event = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.TABLE
        )
        assert table_event["payload"]["rows"] == [["AC/DC"]]

    def test_show_chart_emits_chart_event(self, conversation_with_messages):
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
                                "id": "call_chart",
                                "name": "show_chart",
                                "args": json.dumps(
                                    {
                                        "chart_type": "bar",
                                        "labels": ["EMEA", "APAC"],
                                        "series": [
                                            {"name": "Ingresos", "values": [100, 200]}
                                        ],
                                    }
                                ),
                            }
                        ],
                    ),
                    {},
                ),
            }
        )
        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=json.dumps(
                            {
                                "ok": True,
                                "displayed_to_user": True,
                                "point_count": 2,
                            }
                        ),
                        name="show_chart",
                        tool_call_id="call_chart",
                    ),
                    {},
                ),
            }
        )

        chart_event = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.CHART
        )
        tool_end = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.TOOL_END
        )
        assert chart_event["payload"]["labels"] == ["EMEA", "APAC"]
        assert chart_event["payload"]["datasets"][0]["data"] == [100.0, 200.0]
        assert chart_event["payload"]["tool_call_id"] == "call_chart"
        assert tool_end["payload"]["tool"] == "show_chart"
        assert tool_end["payload"]["output_summary"] == "Gráfico mostrado"

    def test_show_chart_tool_start_includes_chart_type(self, conversation_with_messages):
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
                                "id": "call_line",
                                "name": "show_chart",
                                "args": '{"chart_type": "line", "labels":',
                            }
                        ],
                    ),
                    {},
                ),
            }
        )

        tool_start = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.TOOL_START
        )
        assert tool_start["payload"]["chart_type"] == "line"

    def test_show_chart_tool_start_emits_immediately_without_chart_type(
        self, conversation_with_messages
    ):
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
                        tool_call_chunks=[{"id": "call_pie", "name": "show_chart", "args": ""}],
                    ),
                    {},
                ),
            }
        )

        tool_start = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.TOOL_START
        )
        assert tool_start["payload"]["tool"] == "show_chart"
        assert "chart_type" not in tool_start["payload"]

        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    AIMessageChunk(
                        content="",
                        tool_call_chunks=[
                            {
                                "id": "call_pie",
                                "name": "show_chart",
                                "args": '{"chart_type":"pie","labels":["A"]',
                            }
                        ],
                    ),
                    {},
                ),
            }
        )

        assert (
            sum(
                1
                for item in emitted
                if item["event_type"] == AgentEvent.EventType.TOOL_START
            )
            == 1
        )

    def test_stream_handler_emits_file_created(self, conversation_with_messages):
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

        from apps.agent.tools.document import _DOCUMENT_DISPLAY_REGISTRY

        file_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        _DOCUMENT_DISPLAY_REGISTRY["call_doc"] = {
            "file_id": file_id,
            "name": "Informe.docx",
            "ext": "DOCX",
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "meta": "Document · 1 página",
            "version": 1,
            "download_url": f"/files/{file_id}/download/",
            "preview_url": f"/files/{file_id}/preview/",
            "updated": False,
        }

        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=json.dumps(
                            {
                                "ok": True,
                                "action": "created",
                                "file_id": file_id,
                                "name": "Informe.docx",
                                "version": 1,
                            }
                        ),
                        name="create_document",
                        tool_call_id="call_doc",
                    ),
                    {},
                ),
            }
        )

        file_event = next(
            item for item in emitted if item["event_type"] == AgentEvent.EventType.FILE_CREATED
        )
        assert file_event["payload"]["file_id"] == file_id
        assert file_event["payload"]["name"] == "Informe.docx"

    def test_stream_handler_emits_file_created_for_spreadsheet(self, conversation_with_messages):
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

        from apps.agent.tools.spreadsheet import _SPREADSHEET_DISPLAY_REGISTRY

        file_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        _SPREADSHEET_DISPLAY_REGISTRY["call_sheet"] = {
            "file_id": file_id,
            "name": "Ventas.xlsx",
            "ext": "XLSX",
            "kind": "sheet",
            "format": "xlsx",
            "meta": "Spreadsheet · 1 hoja",
            "version": 1,
            "download_url": f"/files/{file_id}/download/",
            "preview_url": f"/files/{file_id}/preview/",
            "updated": False,
        }

        handler.handle_chunk(
            {
                "type": "messages",
                "ns": (),
                "data": (
                    ToolMessage(
                        content=json.dumps(
                            {
                                "ok": True,
                                "action": "created",
                                "file_id": file_id,
                                "name": "Ventas.xlsx",
                                "version": 1,
                            }
                        ),
                        name="create_spreadsheet",
                        tool_call_id="call_sheet",
                    ),
                    {},
                ),
            }
        )

        file_events = [
            item for item in emitted if item["event_type"] == AgentEvent.EventType.FILE_CREATED
        ]
        assert len(file_events) == 1
        assert file_events[0]["payload"]["file_id"] == file_id
        assert file_events[0]["payload"]["kind"] == "sheet"
