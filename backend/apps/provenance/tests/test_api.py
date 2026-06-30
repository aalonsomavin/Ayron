import json

import pytest
from django.urls import reverse

from apps.agent.context import reset_agent_context, set_agent_backend, set_agent_context
from apps.agent.tests.dict_workspace_backend import DictWorkspaceBackend
from apps.agent.tools.html_report import run_publish_html_artifact
from apps.agent.workspace import draft_artifact_path, write_workspace_file
from apps.chat.models import Conversation, Message
from apps.files.models import File
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink


SINGLE_KPI_DASHBOARD_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Ingresos</div>
          <div class="ay-dash-kpi-value" data-ay-claim="kpi-total-revenue">$1.28M</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provapi", password="pass")


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="provapiother", password="pass")


@pytest.fixture
def conversation(user):
    conv = Conversation.objects.create(user=user, title="Provenance API test")
    Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="")
    return conv


@pytest.fixture
def integration(db):
    return Integration.objects.create(
        slug="mexar-api-test",
        name="Mexar Pharma — Producción",
        type=Integration.Type.POSTGRES,
        config={
            "display": {
                "status": "connected",
                "status_label": "Conectada",
            }
        },
    )


@pytest.fixture
def data_access(conversation, integration):
    message = conversation.messages.first()
    return DataAccess.objects.create(
        conversation=conversation,
        message=message,
        integration=integration,
        tool_call_id="call_api_sql",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT SUM(total) AS total FROM invoice"},
        response_summary={
            "tables": ["invoice"],
            "columns": ["total"],
            "row_count": 412,
            "truncated": False,
            "user_summary": "Consulta de ingresos totales.",
            "preview_rows": [{"total": 2328.6}],
        },
    )


@pytest.fixture
def dashboard_claim(user, conversation, data_access):
    reset_agent_context()
    backend = DictWorkspaceBackend()
    set_agent_backend(backend)
    set_agent_context(conversation, user, message=conversation.messages.first())

    path = draft_artifact_path()
    write_workspace_file(backend, path, SINGLE_KPI_DASHBOARD_HTML)
    provenance = [
        {
            "claim_key": "kpi-total-revenue",
            "label": "Ingresos totales",
            "tool_call_ids": ["call_api_sql"],
            "definition": {
                "metric": "SUM(total)",
                "dataset_ref": "embedded:analytics-data",
                "base_filters": "sin filtros de fecha",
            },
            "transformation": "SUM(total) · redondeo 2 dec",
        }
    ]
    result = json.loads(
        run_publish_html_artifact(
            path,
            "Ventas",
            filename="ventas.html",
            provenance=provenance,
        )
    )
    reset_agent_context()
    assert result["ok"] is True
    file_obj = File.objects.get(id=result["file_id"])
    claim = DataClaim.objects.get(artifact_file=file_obj, claim_key="kpi-total-revenue")
    return claim, file_obj


@pytest.mark.django_db
class TestProvenanceDataAccessApi:
    def test_sql_access_kind_shape(self, client, user, data_access):
        client.force_login(user)
        url = reverse("provenance:data_access_detail", kwargs={"data_access_id": data_access.id})
        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == str(data_access.id)
        assert payload["access_kind"] == "sql"
        assert payload["tool_call_id"] == "call_api_sql"
        assert payload["sql"] == "SELECT SUM(total) AS total FROM invoice"
        assert payload["tables"] == ["invoice"]
        assert payload["columns"] == ["total"]
        assert payload["row_count"] == 412
        assert payload["truncated"] is False
        assert payload["integration"]["name"] == "Mexar Pharma — Producción"
        assert payload["integration"]["type"] == "postgres"
        assert payload["integration"]["status"] == "connected"
        assert "executed_at" in payload
        assert "preview_table" not in payload

    def test_data_access_by_tool_call_id(self, client, user, conversation, data_access):
        client.force_login(user)
        url = reverse(
            "provenance:conversation_data_access_lookup",
            kwargs={"conversation_id": conversation.id},
        )
        response = client.get(url, {"tool_call_id": "call_api_sql"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == str(data_access.id)
        assert payload["sql"] == "SELECT SUM(total) AS total FROM invoice"
        assert payload["access_kind"] == "sql"

    def test_data_access_lookup_requires_tool_call_id(self, client, user, conversation):
        client.force_login(user)
        url = reverse(
            "provenance:conversation_data_access_lookup",
            kwargs={"conversation_id": conversation.id},
        )
        response = client.get(url)

        assert response.status_code == 400

    def test_forbidden_for_other_user_data_access(self, client, other_user, data_access):
        client.force_login(other_user)
        url = reverse("provenance:data_access_detail", kwargs={"data_access_id": data_access.id})
        response = client.get(url)

        assert response.status_code == 404

    def test_forbidden_for_other_user_conversation_lookup(
        self, client, other_user, conversation, data_access
    ):
        client.force_login(other_user)
        url = reverse(
            "provenance:conversation_data_access_lookup",
            kwargs={"conversation_id": conversation.id},
        )
        response = client.get(url, {"tool_call_id": "call_api_sql"})

        assert response.status_code == 404

    def test_unauthenticated_returns_redirect(self, client, data_access):
        url = reverse("provenance:data_access_detail", kwargs={"data_access_id": data_access.id})
        response = client.get(url)

        assert response.status_code == 302


@pytest.mark.django_db
class TestProvenanceClaimApi:
    def test_claim_detail_shape(self, client, user, dashboard_claim, data_access):
        claim, _file_obj = dashboard_claim
        client.force_login(user)
        url = reverse("provenance:claim_detail", kwargs={"claim_id": claim.id})
        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["claim"] == {
            "id": str(claim.id),
            "claim_key": "kpi-total-revenue",
            "label": "Ingresos totales",
            "definition": {
                "metric": "SUM(total)",
                "dataset_ref": "embedded:analytics-data",
                "base_filters": "sin filtros de fecha",
            },
            "surface": "dashboard_kpi",
            "artifact_version": claim.artifact_version,
        }
        assert payload["transformation"] == "SUM(total) · redondeo 2 dec"
        assert len(payload["data_accesses"]) == 1
        assert payload["data_accesses"][0]["id"] == str(data_access.id)
        assert payload["data_accesses"][0]["access_kind"] == "sql"
        assert payload["data_accesses"][0]["sql"] == "SELECT SUM(total) AS total FROM invoice"
        assert payload["source"]["name"] == "Mexar Pharma — Producción"
        assert payload["source"]["type"] == "postgres"
        assert payload["source"]["status"] == "connected"
        assert len(payload["provenance_links"]) == 1
        assert payload["provenance_links"][0]["ordinal"] == 0
        assert payload["provenance_links"][0]["transformation"] == "SUM(total) · redondeo 2 dec"

    def test_claim_by_file_and_key(self, client, user, dashboard_claim, data_access):
        claim, file_obj = dashboard_claim
        client.force_login(user)
        url = reverse(
            "provenance:file_claim_detail",
            kwargs={"file_id": file_obj.id, "claim_key": "kpi-total-revenue"},
        )
        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["claim"]["id"] == str(claim.id)
        assert payload["claim"]["claim_key"] == "kpi-total-revenue"
        assert payload["data_accesses"][0]["id"] == str(data_access.id)

    def test_forbidden_for_other_user_claim(self, client, other_user, dashboard_claim):
        claim, _file_obj = dashboard_claim
        client.force_login(other_user)
        url = reverse("provenance:claim_detail", kwargs={"claim_id": claim.id})
        response = client.get(url)

        assert response.status_code == 404

    def test_forbidden_for_other_user_file_claim(self, client, other_user, dashboard_claim):
        _claim, file_obj = dashboard_claim
        client.force_login(other_user)
        url = reverse(
            "provenance:file_claim_detail",
            kwargs={"file_id": file_obj.id, "claim_key": "kpi-total-revenue"},
        )
        response = client.get(url)

        assert response.status_code == 404

    def test_file_claim_not_found(self, client, user, dashboard_claim):
        _claim, file_obj = dashboard_claim
        client.force_login(user)
        url = reverse(
            "provenance:file_claim_detail",
            kwargs={"file_id": file_obj.id, "claim_key": "missing-key"},
        )
        response = client.get(url)

        assert response.status_code == 404

    def test_inline_claim_detail(self, client, user, conversation, data_access):
        message = conversation.messages.first()
        claim = DataClaim.objects.create(
            conversation=conversation,
            message=message,
            claim_key="chat-table-call_inline",
            surface=DataClaim.Surface.CHAT_TABLE,
            label="Tabla de ventas",
            definition={},
        )
        ProvenanceLink.objects.create(
            claim=claim,
            data_access=data_access,
            transformation="",
            ordinal=0,
        )

        client.force_login(user)
        url = reverse("provenance:claim_detail", kwargs={"claim_id": claim.id})
        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["claim"]["surface"] == "chat_table"
        assert payload["claim"]["claim_key"] == "chat-table-call_inline"
        assert payload["transformation"] == ""
        assert len(payload["data_accesses"]) == 1

    def test_claim_detail_renders_html_like_tool_trace(self, client, user, conversation, data_access):
        message = conversation.messages.first()
        claim = DataClaim.objects.create(
            conversation=conversation,
            message=message,
            claim_key="chat-table-call_html",
            surface=DataClaim.Surface.CHAT_TABLE,
            label="Productos con mayor presión competitiva",
            definition={},
        )
        ProvenanceLink.objects.create(
            claim=claim,
            data_access=data_access,
            transformation="",
            ordinal=0,
        )

        client.force_login(user)
        url = reverse("provenance:claim_detail", kwargs={"claim_id": claim.id})
        response = client.get(url, HTTP_ACCEPT="text/html")
        content = response.content.decode()

        assert response.status_code == 200
        assert "ay-provenance-sql" in content
        assert "Origen de los datos" in content
        assert "Consulta de ingresos totales." in content
        assert "Ver consulta SQL" in content
        assert "Conectada" not in content
        assert "data-provenance-run" not in content
        assert "Ver datos completos" not in content
        assert "PostgreSQL · Mexar Pharma — Producción" in content
        assert "ay-data-table" in content
