import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.agent.events import persist_event
from apps.chat.models import AgentEvent, Conversation, Message
from apps.chat.views import _content_blocks_for_message, _hero_title, serialize_agent_event
from apps.files.parsers import parse_upload
from apps.files.services import save_uploaded_file, serialize_file_for_ui
from apps.files.tests.test_parsers_xlsx import build_sample_xlsx_bytes

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

        assert response.status_code == 200
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

        payload = response.json()
        assert payload["assistant_message_id"] == messages[1].id

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
class TestUploadFile:
    def test_upload_xlsx(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:upload", kwargs={"conversation_id": conversation.id})
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = client.post(url, {"file": upload})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["file_id"]
        assert payload["ext"] == "XLSX"

    def test_upload_rejects_unsupported_format(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:upload", kwargs={"conversation_id": conversation.id})
        upload = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = client.post(url, {"file": upload})
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["error"]


@pytest.mark.django_db
class TestSendMessageWithFiles:
    def test_send_with_file_ids_creates_user_file_events(self, client, user, conversation):
        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        file_obj = save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=build_sample_xlsx_bytes(),
            parsed=parsed,
        )
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-files")
            response = client.post(
                url,
                {
                    "content": "Analiza el Excel",
                    "file_ids": json.dumps([str(file_obj.id)]),
                },
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 200
        user_message = conversation.messages.filter(role=Message.Role.USER).first()
        events = AgentEvent.objects.filter(
            message=user_message,
            event_type=AgentEvent.EventType.FILE_CREATED,
        )
        assert events.count() == 1
        blocks = _content_blocks_for_message(user_message, user=user)
        assert any(block["type"] == "files" for block in blocks)


@pytest.mark.django_db
class TestStopConversation:
    def test_stop_when_processing(self, client, user, conversation):
        conversation.status = Conversation.Status.PROCESSING
        conversation.celery_task_id = "task-456"
        conversation.save()
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        client.force_login(user)
        url = reverse("chat:stop", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.views.request_cancel") as mock_cancel:
            with patch("apps.chat.views.celery_app.control.revoke") as mock_revoke:
                with patch("apps.chat.views.rollback_thread_to_turn") as mock_rollback:
                    with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                        mock_get_redis.return_value = MagicMock()
                        response = client.post(url)

        assert response.status_code == 204
        mock_cancel.assert_called_once_with(conversation.id)
        mock_revoke.assert_called_once_with("task-456", terminate=True)
        mock_rollback.assert_not_called()

        conversation.refresh_from_db()
        assert conversation.status == Conversation.Status.ACTIVE
        assert AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.DONE,
            message=assistant_message,
            payload={"cancelled": True},
        ).exists()

    def test_stop_rolls_back_checkpoint_when_user_message_exists(self, client, user, conversation):
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Cancel me",
        )
        conversation.status = Conversation.Status.PROCESSING
        conversation.save()
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        client.force_login(user)
        url = reverse("chat:stop", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.views.request_cancel"):
            with patch("apps.chat.views.celery_app.control.revoke"):
                with patch("apps.chat.views.rollback_thread_to_turn") as mock_rollback:
                    with patch("apps.agent.events.get_redis_client") as mock_get_redis:
                        mock_get_redis.return_value = MagicMock()
                        response = client.post(url)

        assert response.status_code == 204
        mock_rollback.assert_called_once_with(
            conversation,
            user_message,
            include_user_message=True,
        )

    def test_stop_rejects_when_not_processing(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:stop", kwargs={"conversation_id": conversation.id})
        response = client.post(url)
        assert response.status_code == 400

    def test_stop_other_user_gets_404(self, client, other_user, conversation):
        conversation.status = Conversation.Status.PROCESSING
        conversation.save()
        client.force_login(other_user)
        url = reverse("chat:stop", kwargs={"conversation_id": conversation.id})
        response = client.post(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestRetryMessage:
    def test_retry_reuses_cancelled_turn(self, client, user, conversation):
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Haceme una tabla",
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Partial",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Partial"},
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.DONE,
            payload={"cancelled": True},
            sequence_number=1,
        )

        client.force_login(user)
        url = reverse("chat:retry", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.views.run_agent_conversation.delay") as mock_delay:
            with patch("apps.chat.views.rollback_thread_to_turn") as mock_rollback:
                mock_delay.return_value = MagicMock(id="task-retry-1")
                response = client.post(url, {"assistant_message_id": assistant_message.id})

        assert response.status_code == 200
        mock_rollback.assert_called_once_with(
            conversation,
            user_message,
            include_user_message=False,
        )
        data = response.json()
        assert data["assistant_message_id"] == assistant_message.id
        assert data["last_sequence"] == -1

        mock_delay.assert_called_once_with(
            str(conversation.id),
            user_message.id,
            assistant_message.id,
        )

        conversation.refresh_from_db()
        assert conversation.status == Conversation.Status.PROCESSING
        assert conversation.celery_task_id == "task-retry-1"

        assistant_message.refresh_from_db()
        assert assistant_message.content == ""
        assert not AgentEvent.objects.filter(message=assistant_message).exists()

        assert Message.objects.filter(conversation=conversation).count() == 2

    def test_retry_rejects_when_not_cancelled(self, client, user, conversation):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hello",
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Done",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.DONE,
            payload={},
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:retry", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"assistant_message_id": assistant_message.id})
        assert response.status_code == 400

    def test_retry_rejects_when_processing(self, client, user, conversation):
        conversation.status = Conversation.Status.PROCESSING
        conversation.save()
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Hello",
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.DONE,
            payload={"cancelled": True},
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:retry", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"assistant_message_id": assistant_message.id})
        assert response.status_code == 400
        assert Message.objects.filter(conversation=conversation).count() == 2


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
                "tool_subtitle": "Mexar Pharma database",
                "tool_call_id": "call_1",
                "input": {},
            },
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:events", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        data = response.json()

        assert data["events"][0]["tool_label"] == "Revisó tablas disponibles"
        assert data["events"][0]["tool_subtitle"] == "Mexar Pharma"
        assert data["events"][0]["tool_tag"] == "Base de datos"

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

        assert data["tool_label"] == "Consultó datos de Artist"
        assert data["tool_subtitle"] == 'SELECT * FROM "Artist" LIMIT 5'
        assert data["tool_tag"] == "SQL"
        assert data["tool_icon"] == "terminal"

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
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Show me the table",
        )
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

    def test_content_blocks_split_text_around_tools(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Voy a buscar los datos.Analizo los resultados.Aquí está el resumen.",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Voy a buscar los datos."},
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_call_id": "call_1",
                "input": {"sql": 'SELECT * FROM "Album"'},
            },
            sequence_number=1,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Analizo los resultados."},
            sequence_number=2,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOOL_END,
            payload={"tool": "run_sql_query", "tool_call_id": "call_1"},
            sequence_number=3,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Aquí está el resumen."},
            sequence_number=4,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert [block["type"] for block in blocks] == ["text", "text", "text"]
        assert blocks[0]["content"] == "Voy a buscar los datos."
        assert blocks[1]["content"] == "Analizo los resultados."
        assert blocks[2]["content"] == "Aquí está el resumen."

    def test_content_blocks_merge_consecutive_tokens(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Hello world",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Hello "},
            sequence_number=0,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "world"},
            sequence_number=1,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert blocks[0]["content"] == "Hello world"

    def test_detail_renders_chart_events(self, client, user, conversation):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Show me the chart",
        )
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
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Show data",
        )
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
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="How many albums?",
        )
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
        assert "ay-tool-trace__tag" in content
        assert "Buscó datos 1 vez, mostró 1 tabla" in content
        assert "Listo" in content

    def test_detail_renders_cancelled_notice(self, client, user, conversation):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Genera un dashboard",
        )
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
                "tool_subtitle": 'SELECT 1',
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

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        content = response.content.decode()

        assert "Detuviste la generación" in content
        assert "ay-msg-agent--cancelled" in content
        assert "ay-tool-trace" in content
        assert "Reintentar" in content

    def test_processing_active_assistant_not_ssr_rendered(self, client, user, conversation):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="First question",
        )
        completed_assistant = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="First answer.",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=completed_assistant,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "First answer."},
            sequence_number=0,
        )

        conversation.status = Conversation.Status.PROCESSING
        conversation.save()
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Second question",
        )
        active_assistant = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=active_assistant,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": "run_sql_query",
                "tool_label": "Buscando datos",
                "tool_subtitle": 'SELECT * FROM "Album"',
                "tool_call_id": "call_1",
                "input": {"sql": 'SELECT * FROM "Album"'},
            },
            sequence_number=1,
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=active_assistant,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": "Working on it..."},
            sequence_number=2,
        )

        client.force_login(user)
        url = reverse("chat:detail", kwargs={"conversation_id": conversation.id})
        response = client.get(url)
        content = response.content.decode()

        assert (
            f'<div class="ay-msg-agent" data-message-id="{completed_assistant.id}">'
            in content
        )
        assert "First answer." in content
        assert (
            f'<div class="ay-msg-agent" data-message-id="{active_assistant.id}">'
            not in content
        )
        assert "Working on it..." not in content
        assert f"activeMessageId = {active_assistant.id}" in content

    def test_content_blocks_include_file(self, conversation):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.FILE_CREATED,
            payload={
                "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Informe.docx",
                "ext": "DOCX",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "meta": "Document · 1 página",
                "version": 1,
                "download_url": "/files/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download/",
                "preview_url": "/files/a1b2c3d4-e5f6-7890-abcd-ef1234567890/preview/",
            },
            sequence_number=0,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "files"
        assert blocks[0]["files"][0]["name"] == "Informe.docx"

    def test_content_blocks_exclude_context_from_assistant(self, user, conversation):
        from apps.files.parsers import parse_upload
        from apps.files.services import save_uploaded_file
        from apps.files.tests.test_parsers_xlsx import build_sample_xlsx_bytes

        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        file_obj = save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=build_sample_xlsx_bytes(),
            parsed=parsed,
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.FILE_CREATED,
            payload=serialize_file_for_ui(file_obj, user=user),
            sequence_number=0,
        )

        blocks = _content_blocks_for_message(assistant_message, user=user)

        assert blocks == []

    def test_content_blocks_hydrate_renamed_dashboard_name(self, user, conversation):
        from apps.files.models import HTML_MIME
        from apps.files.services import rename_dashboard_file, save_generated_file

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "dashboard-ventas",
            "subtitle": "",
            "html": dashboard_html,
            "body_html": dashboard_html,
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="dashboard-ventas.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        rename_dashboard_file(file_obj, "dashboard-hyalufresh")

        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.FILE_CREATED,
            payload={
                "file_id": str(file_obj.id),
                "name": "dashboard-ventas.html",
                "ext": "HTML",
                "format": "html",
                "kind": "dashboard",
                "meta": "Dashboard",
                "version": 1,
                "download_url": f"/files/{file_obj.id}/download/",
                "preview_url": f"/files/{file_obj.id}/preview/",
                "open_expanded": True,
            },
            sequence_number=0,
        )

        blocks = _content_blocks_for_message(assistant_message)

        assert blocks[0]["files"][0]["name"] == "dashboard-hyalufresh"


@pytest.mark.django_db
class TestConversationNew:
    def test_new_redirects_to_list(self, client, user):
        client.force_login(user)
        response = client.get(reverse("chat:new"))
        assert response.status_code == 302
        assert response.url == reverse("chat:list")
        assert Conversation.objects.filter(user=user).count() == 0

    def test_list_does_not_create_conversation(self, client, user):
        client.force_login(user)
        response = client.get(reverse("chat:list"))
        assert response.status_code == 200
        assert Conversation.objects.filter(user=user).count() == 0
        content = response.content.decode()
        assert "ay-chat-empty__title" in content


@pytest.mark.django_db
class TestHeroTitle:
    def test_hero_title_returns_generic_title(self, user):
        with patch("apps.chat.views.random.choice", side_effect=lambda opts: opts[0]):
            assert _hero_title(user) == "¿Qué quieres saber hoy?"

    def test_hero_title_greets_user_by_first_name(self, user):
        user.first_name = "Alejandro"
        user.save()
        with patch("apps.chat.views.random.choice", side_effect=lambda opts: opts[-1]):
            assert "Alejandro" in _hero_title(user)

    def test_hero_title_capitalizes_username(self, user):
        user.first_name = ""
        user.last_name = ""
        user.username = "alejandro"
        user.save()
        with patch("apps.chat.views.random.choice", side_effect=lambda opts: opts[-1]):
            assert "Alejandro" in _hero_title(user)


@pytest.mark.django_db
class TestConversationStart:
    def test_start_creates_conversation_on_first_message(self, client, user):
        client.force_login(user)
        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-456")
            response = client.post(reverse("chat:start"), {"content": "Top artists by albums"})

        assert response.status_code == 302
        conversation = Conversation.objects.get(user=user)
        assert str(conversation.id) in response.url
        assert conversation.title == "Top artists by albums"
        assert conversation.status == Conversation.Status.PROCESSING
        mock_task.delay.assert_called_once()

    def test_start_rejects_empty_content(self, client, user):
        client.force_login(user)
        response = client.post(reverse("chat:start"), {"content": "   "})
        assert response.status_code == 400
        assert Conversation.objects.filter(user=user).count() == 0

    def test_start_with_file_only_uses_filename_as_title(self, client, user):
        client.force_login(user)
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload_response = client.post(reverse("chat:upload_staging"), {"file": upload})
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-file-only")
            response = client.post(
                reverse("chat:start"),
                {"file_ids": json.dumps([file_id])},
            )

        assert response.status_code == 302
        conversation = Conversation.objects.get(user=user)
        assert conversation.title == "ventas.xlsx"
        assert conversation.messages.filter(role=Message.Role.USER).count() == 1
        mock_task.delay.assert_called_once()

    def test_start_with_staging_files_claims_orphan_files(self, client, user):
        client.force_login(user)
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload_response = client.post(reverse("chat:upload_staging"), {"file": upload})
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        assert Conversation.objects.filter(user=user).count() == 0

        with patch("apps.chat.views.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-789")
            response = client.post(
                reverse("chat:start"),
                {
                    "content": "Analiza este Excel",
                    "file_ids": json.dumps([file_id]),
                },
            )

        assert response.status_code == 302
        assert Conversation.objects.filter(user=user).count() == 1
        conversation = Conversation.objects.get(user=user)
        assert conversation.title == "Analiza este Excel"
        assert conversation.messages.filter(role=Message.Role.USER).count() == 1
        assert AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.FILE_CREATED,
        ).count() == 1
        mock_task.delay.assert_called_once()


@pytest.mark.django_db
class TestStagingUpload:
    def test_staging_upload_does_not_create_conversation(self, client, user):
        client.force_login(user)
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = client.post(reverse("chat:upload_staging"), {"file": upload})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["file_id"]
        assert Conversation.objects.filter(user=user).count() == 0

    def test_discard_staging_file(self, client, user):
        client.force_login(user)
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload_response = client.post(reverse("chat:upload_staging"), {"file": upload})
        file_id = upload_response.json()["file_id"]

        response = client.post(reverse("chat:discard_staging", kwargs={"file_id": file_id}))
        assert response.status_code == 200
        from apps.files.models import File

        assert not File.objects.filter(id=file_id).exists()

    def test_discard_staging_file_other_user_404(self, client, user, other_user):
        client.force_login(user)
        upload = SimpleUploadedFile(
            "ventas.xlsx",
            build_sample_xlsx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload_response = client.post(reverse("chat:upload_staging"), {"file": upload})
        file_id = upload_response.json()["file_id"]

        client.force_login(other_user)
        response = client.post(reverse("chat:discard_staging", kwargs={"file_id": file_id}))
        assert response.status_code == 404


@pytest.mark.django_db
class TestEmptyConversationCleanup:
    def test_sidebar_hides_empty_conversations(self, client, user):
        empty = Conversation.objects.create(user=user)
        with_messages = Conversation.objects.create(user=user, title="Active chat")
        Message.objects.create(
            conversation=with_messages,
            role=Message.Role.USER,
            content="Hi",
        )
        client.force_login(user)
        response = client.get(reverse("chat:list"))
        content = response.content.decode()
        assert "Active chat" in content
        assert str(empty.id) not in content

    def test_empty_conversation_detail_redirects_to_list(self, client, user):
        empty = Conversation.objects.create(user=user)
        client.force_login(user)
        response = client.get(reverse("chat:detail", kwargs={"conversation_id": empty.id}))
        assert response.status_code == 302
        assert response.url == reverse("chat:list")
        assert not Conversation.objects.filter(id=empty.id).exists()


@pytest.mark.django_db
class TestConversationDraftLegacy:
    def test_draft_creates_empty_conversation(self, client, user):
        client.force_login(user)
        response = client.post(reverse("chat:draft"))
        assert response.status_code == 200
        payload = response.json()
        conversation = Conversation.objects.get(id=payload["conversation_id"], user=user)
        assert conversation.status == Conversation.Status.ACTIVE
        assert conversation.messages.count() == 0


@pytest.mark.django_db
class TestConversationSidebarActions:
    def test_rename_updates_title(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:rename", kwargs={"conversation_id": conversation.id})
        response = client.post(
            url,
            {
                "title": "Ventas Q1",
                "active_conversation_id": str(conversation.id),
            },
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        conversation.refresh_from_db()
        assert conversation.title == "Ventas Q1"
        assert b"Ventas Q1" in response.content
        assert b'sidebar-chat-' in response.content

    def test_rename_rejects_empty_title(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:rename", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"title": "   "}, HTTP_HX_REQUEST="true")
        assert response.status_code == 400

    def test_rename_other_user_404(self, client, other_user, conversation):
        client.force_login(other_user)
        url = reverse("chat:rename", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"title": "Nope"}, HTTP_HX_REQUEST="true")
        assert response.status_code == 404

    def test_delete_removes_conversation(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:delete", kwargs={"conversation_id": conversation.id})
        response = client.post(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert not Conversation.objects.filter(id=conversation.id).exists()
        assert "ayronToast" in response.headers.get("HX-Trigger", "")

    def test_delete_active_conversation_redirects(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:delete", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"active": "1"}, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == reverse("chat:list")
        assert "ayronToast" in response.headers.get("HX-Trigger", "")

    def test_delete_other_user_404(self, client, other_user, conversation):
        client.force_login(other_user)
        url = reverse("chat:delete", kwargs={"conversation_id": conversation.id})
        response = client.post(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 404
        assert Conversation.objects.filter(id=conversation.id).exists()

    def test_delete_conversation_preserves_files(self, client, user, conversation):
        from apps.files.models import HTML_MIME
        from apps.files.services import save_generated_file

        content = {
            "format": "html",
            "html_kind": "report",
            "title": "Informe Q1",
            "html": "<html></html>",
            "body_html": "<html></html>",
            "full_document": True,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Informe Q1.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        file_id = file_obj.id

        client.force_login(user)
        url = reverse("chat:delete", kwargs={"conversation_id": conversation.id})
        response = client.post(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert not Conversation.objects.filter(id=conversation.id).exists()
        file_obj.refresh_from_db()
        assert file_obj.conversation_id is None

    def test_delete_conversation_preserves_saved_dashboard(self, client, user, conversation):
        from apps.files.models import HTML_MIME, SavedDashboard
        from apps.files.services import list_saved_dashboards, save_dashboard, save_generated_file

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "412 facturas",
            "html": dashboard_html,
            "body_html": dashboard_html,
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Ventas.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        save_dashboard(user, file_obj)

        client.force_login(user)
        url = reverse("chat:delete", kwargs={"conversation_id": conversation.id})
        response = client.post(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert not Conversation.objects.filter(id=conversation.id).exists()
        assert SavedDashboard.objects.filter(user=user, file=file_obj).exists()
        saved = list(list_saved_dashboards(user))
        assert len(saved) == 1
        assert saved[0].file_id == file_obj.id
        file_obj.refresh_from_db()
        assert file_obj.conversation_id is None


@pytest.fixture
def clarification_payload():
    return {
        "tool_call_id": "call-clarify-1",
        "questions": [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "hint": "",
                "kind": "choice",
                "selection": "single",
                "optional": False,
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                    {"id": "other", "label": "Otro:"},
                ],
            },
            {
                "id": "notas",
                "title": "Notas adicionales",
                "hint": "",
                "kind": "text",
                "selection": "single",
                "optional": True,
                "options": [],
            },
        ],
        "allow_skip": True,
        "submit_label": "Analizar con esto",
        "submitted": False,
        "skipped": False,
        "answers": None,
    }


@pytest.mark.django_db
class TestClarificationViews:
    def test_send_rejects_while_awaiting_clarification(self, client, user, conversation):
        conversation.status = Conversation.Status.AWAITING_CLARIFICATION
        conversation.save()
        client.force_login(user)
        url = reverse("chat:send", kwargs={"conversation_id": conversation.id})
        response = client.post(url, {"content": "Otra pregunta"})
        assert response.status_code == 400

    def test_wizard_renders_first_step(self, client, user, conversation, clarification_payload):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Precisemos algunas cosas.",
        )
        conversation.status = Conversation.Status.AWAITING_CLARIFICATION
        conversation.save()
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CLARIFICATION,
            payload=clarification_payload,
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:clarification_wizard", kwargs={"conversation_id": conversation.id})
        response = client.get(
            url,
            {
                "assistant_message_id": assistant_message.id,
                "tool_call_id": clarification_payload["tool_call_id"],
                "step": "0",
            },
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assert b"Paso 1 de 2" in response.content
        assert b"Periodo a analizar" in response.content
        assert b"Otro:" in response.content
        assert b"clarification-call-clarify-1" in response.content

    def test_step_next_renders_second_step(self, client, user, conversation, clarification_payload):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        conversation.status = Conversation.Status.AWAITING_CLARIFICATION
        conversation.save()
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CLARIFICATION,
            payload=clarification_payload,
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:clarification_step", kwargs={"conversation_id": conversation.id})
        response = client.post(
            url,
            {
                "assistant_message_id": assistant_message.id,
                "tool_call_id": clarification_payload["tool_call_id"],
                "step": "0",
                "direction": "next",
                "answers_json": "{}",
                "answer_periodo": "year",
            },
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assert b"Paso 2 de 2" in response.content
        assert b"Notas adicionales" in response.content

    def test_submit_skip_resumes_agent(self, client, user, conversation, clarification_payload):
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Analiza ventas",
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
        )
        conversation.status = Conversation.Status.AWAITING_CLARIFICATION
        conversation.save()
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CLARIFICATION,
            payload=clarification_payload,
            sequence_number=0,
        )

        client.force_login(user)
        url = reverse("chat:clarification_submit", kwargs={"conversation_id": conversation.id})

        with patch("apps.chat.clarification.run_agent_conversation") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-resume")
            response = client.post(
                url,
                {
                    "assistant_message_id": assistant_message.id,
                    "tool_call_id": clarification_payload["tool_call_id"],
                    "step": "0",
                    "answers_json": "{}",
                    "skipped": "1",
                },
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 200
        assert b"Analizando" not in response.content
        assert response.headers.get("HX-Reswap") == "delete"
        assert "ayronResumeStream" in response.headers.get("HX-Trigger", "")

        conversation.refresh_from_db()
        assert conversation.status == Conversation.Status.PROCESSING
        assert conversation.celery_task_id == "task-resume"

        event = AgentEvent.objects.get(
            conversation=conversation,
            event_type=AgentEvent.EventType.CLARIFICATION,
        )
        assert event.payload["submitted"] is True
        assert event.payload["skipped"] is True

        mock_task.delay.assert_called_once()
        args = mock_task.delay.call_args.args
        assert args[0] == str(conversation.id)
        assert args[1] == user_message.id
        assert args[2] == assistant_message.id

    def test_content_blocks_include_clarification(self, user, conversation, clarification_payload):
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Intro",
        )
        AgentEvent.objects.create(
            conversation=conversation,
            message=assistant_message,
            event_type=AgentEvent.EventType.CLARIFICATION,
            payload=clarification_payload,
            sequence_number=0,
        )

        blocks = _content_blocks_for_message(assistant_message, user=user)
        clarification_blocks = [block for block in blocks if block["type"] == "clarification"]
        assert len(clarification_blocks) == 1
        assert clarification_blocks[0]["question"]["id"] == "periodo"
        assert clarification_blocks[0]["total_steps"] == 2
