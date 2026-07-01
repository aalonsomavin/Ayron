import pytest
from django.urls import reverse

from apps.chat.models import AgentEvent, Conversation, Message
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provview", password="pass")


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provother", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user, title="Provenance view test")


@pytest.fixture
def data_access(conversation):
    integration = Integration.objects.create(
        slug="mexar-test",
        name="Mexar Pharma — Producción",
        type=Integration.Type.POSTGRES,
        config={
            "display": {
                "status": "connected",
                "status_label": "Conectada",
            }
        },
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
        tool_call_id="call_detail_test",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT sku, nombre FROM comercial_productos LIMIT 50"},
        response_summary={
            "tables": ["comercial_productos"],
            "columns": ["sku", "nombre"],
            "row_count": 50,
            "truncated": False,
            "user_summary": "Ayron consultó productos para revisar el catálogo comercial.",
            "preview_rows": [{"sku": "A1", "nombre": "Asgen"}],
        },
    )


@pytest.mark.django_db
class TestProvenanceDataAccessView:
    def test_data_access_detail_returns_full_sql(self, client, user, conversation, data_access):
        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "call_detail_test"}, HTTP_ACCEPT="application/json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["sql"] == "SELECT sku, nombre FROM comercial_productos LIMIT 50"
        assert payload["tables"] == ["comercial_productos"]
        assert payload["row_count"] == 50
        assert payload["integration"]["name"] == "Mexar Pharma — Producción"
        assert payload["integration"]["type_label"] == "PostgreSQL"
        assert payload["integration"]["status"] == "connected"
        assert payload["user_summary"] == "Ayron consultó productos para revisar el catálogo comercial."

    def test_data_access_detail_renders_html_partial(self, client, user, conversation, data_access):
        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "call_detail_test"}, HTTP_ACCEPT="text/html")

        content = response.content.decode()
        assert response.status_code == 200
        assert "ay-provenance-sql" in content
        assert "Origen de los datos" in content
        assert "Ayron consultó productos para revisar el catálogo comercial." in content
        assert "data-provenance-ask" in content
        assert "data-provenance-context" in content
        assert '"open_source": "tool_trace"' in content
        assert "call_detail_test" in content
        assert "Ver consulta SQL" not in content
        assert "Conectada" not in content
        assert "data-provenance-run" not in content
        assert "Ver datos completos" not in content
        assert "PostgreSQL · Mexar Pharma — Producción" in content
        assert "ay-data-table" in content

    def test_data_access_detail_view_permissions(self, client, other_user, conversation, data_access):
        client.force_login(other_user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "call_detail_test"})

        assert response.status_code == 404

    def test_data_access_detail_missing_tool_call_returns_404(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "missing_call"})

        assert response.status_code == 404

    def test_failed_sql_query_renders_fallback_detail(self, client, user, conversation):
        Integration.objects.get_or_create(
            slug="mexar-demo",
            defaults={
                "name": "Mexar Pharma — Demo",
                "type": Integration.Type.POSTGRES,
                "is_active": True,
            },
        )
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
                "tool_call_id": "call_failed_sql",
                "tool_label": "Consultó datos de comercial_productos",
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": "Intenté revisar el catálogo comercial.",
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
                "tool_call_id": "call_failed_sql",
                "success": False,
                "error": "Only SELECT queries are allowed",
            },
        )

        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "call_failed_sql"}, HTTP_ACCEPT="text/html")

        content = response.content.decode()
        assert response.status_code == 200
        assert "Intenté revisar el catálogo comercial." in content
        assert "Esta búsqueda no devolvió datos." in content
        assert "data-provenance-ask" in content
        assert "Ver consulta SQL" not in content
        assert "Only SELECT" not in content
        assert "data-provenance-run" not in content

    def test_failed_sql_query_returns_json(self, client, user, conversation):
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
                "tool_call_id": "call_failed_json",
                "input": {
                    "sql": "DELETE FROM comercial_productos",
                    "purpose": "Intenté revisar el catálogo comercial.",
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
                "tool_call_id": "call_failed_json",
                "success": False,
                "error": "Only SELECT queries are allowed",
            },
        )

        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url, {"tool_call_id": "call_failed_json"}, HTTP_ACCEPT="application/json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["failed"] is True
        assert payload["status_message"] == "Esta búsqueda no devolvió datos."
        assert payload["user_summary"] == "Intenté revisar el catálogo comercial."
        assert payload["sql"] == "DELETE FROM comercial_productos"

    def test_data_access_detail_requires_tool_call_id(self, client, user, conversation):
        client.force_login(user)
        url = reverse("chat:provenance_data_access", kwargs={"conversation_id": conversation.id})
        response = client.get(url)

        assert response.status_code == 400
