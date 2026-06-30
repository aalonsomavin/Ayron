import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import reset_agent_context, set_agent_context
from apps.agent.tools.sql import run_sql_query
from apps.chat.models import Conversation, Message
from apps.integrations.models import Integration
from apps.integrations.services import get_demo_integration
from apps.provenance.models import DataAccess
from apps.provenance.recorder import record_data_access
from apps.provenance.services import get_data_access_for_tool_call

User = get_user_model()


def invoke_run_sql_query(sql: str, tool_call_id: str = "call_sql_test"):
    result = run_sql_query.invoke(
        {
            "type": "tool_call",
            "name": "run_sql_query",
            "id": tool_call_id,
            "args": {"sql": sql},
        }
    )
    return result.content if hasattr(result, "content") else result


@pytest.fixture(autouse=True)
def _reset_agent_context():
    reset_agent_context()
    yield
    reset_agent_context()


@pytest.fixture
def conversation(db):
    user = User.objects.create_user(username="provuser", password="pass")
    conv = Conversation.objects.create(user=user, title="Provenance test")
    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content="",
    )
    return conv, message, user


@pytest.mark.django_db
class TestRecordDataAccess:
    def test_record_creates_row(self, conversation):
        conv, message, user = conversation
        integration = Integration.objects.create(
            slug="test-db",
            name="Test DB",
            type=Integration.Type.POSTGRES,
        )
        set_agent_context(conv, user, message=message)

        record_data_access(
            tool_name="run_sql_query",
            tool_call_id="call_abc",
            access_kind="sql",
            request={"sql": "SELECT 1"},
            response_summary={"row_count": 1, "tables": [], "columns": [], "truncated": False},
            integration=integration,
        )

        data_access = DataAccess.objects.get(conversation=conv, tool_call_id="call_abc")
        assert data_access.access_kind == DataAccess.AccessKind.SQL
        assert data_access.request["sql"] == "SELECT 1"
        assert data_access.integration_id == integration.id
        assert data_access.message_id == message.id

    def test_record_without_context_is_noop(self, db):
        record_data_access(
            tool_name="run_sql_query",
            tool_call_id="call_abc",
            access_kind="sql",
            request={"sql": "SELECT 1"},
            response_summary={"row_count": 0},
        )
        assert DataAccess.objects.count() == 0


@pytest.mark.django_db
class TestGetDataAccessForToolCall:
    def test_lookup_by_conversation_and_tool_call_id(self, conversation):
        conv, message, user = conversation
        integration = Integration.objects.create(
            slug="lookup-db",
            name="Lookup DB",
            type=Integration.Type.POSTGRES,
        )
        created = DataAccess.objects.create(
            conversation=conv,
            message=message,
            integration=integration,
            tool_call_id="call_lookup",
            access_kind=DataAccess.AccessKind.SQL,
            request={"sql": "SELECT 1"},
            response_summary={"row_count": 1},
        )

        found = get_data_access_for_tool_call(conv, "call_lookup")
        assert found == created

        assert get_data_access_for_tool_call(conv, "missing") is None


@pytest.mark.django_db
class TestRunSqlQueryRecorder:
    @patch("apps.agent.tools.sql.demo_db_connection")
    def test_successful_query_creates_data_access(self, mock_connection, conversation):
        conv, message, user = conversation
        assert get_demo_integration() is not None
        set_agent_context(conv, user, message=message)

        cursor = MagicMock()
        cursor.fetchmany.return_value = [{"sku": "ASGEN", "marca_comercial": "Asgen"}]
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        mock_connection.return_value = conn

        result = json.loads(
            invoke_run_sql_query(
                "SELECT sku, marca_comercial FROM comercial_productos LIMIT 1",
                tool_call_id="call_record_1",
            )
        )

        assert result["row_count"] == 1
        data_access = DataAccess.objects.get(conversation=conv, tool_call_id="call_record_1")
        assert "comercial_productos" in data_access.response_summary["tables"]
        assert data_access.integration.slug == "mexar-demo"
        assert data_access.request["sql"].startswith("SELECT sku")

    @patch("apps.agent.tools.sql.demo_db_connection")
    def test_failed_query_does_not_create_data_access(self, mock_connection, conversation):
        import psycopg

        conv, message, user = conversation
        assert get_demo_integration() is not None
        set_agent_context(conv, user, message=message)

        cursor = MagicMock()
        cursor.execute.side_effect = psycopg.errors.UndefinedTable("missing")
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        mock_connection.return_value = conn

        result = json.loads(
            invoke_run_sql_query("SELECT * FROM not_a_real_table LIMIT 1")
        )

        assert result["ok"] is False
        assert DataAccess.objects.count() == 0
