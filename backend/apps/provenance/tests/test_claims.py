import json

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import reset_agent_context, set_agent_backend, set_agent_context
from apps.agent.tests.dict_workspace_backend import DictWorkspaceBackend
from apps.agent.tools.chart import pop_chart_display, show_chart
from apps.agent.tools.html_report import run_publish_html_artifact
from apps.agent.tools.table import pop_table_display, show_data_table
from apps.agent.workspace import draft_artifact_path, write_workspace_file
from apps.chat.models import Conversation, Message
from apps.files.models import File
from apps.provenance.claims import extract_claim_keys_from_html, validate_provenance_payload
from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink

User = get_user_model()


PROVENANCE_DASHBOARD_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Ingresos</div>
          <div class="ay-dash-kpi-value" data-ay-claim="kpi-total-revenue">$1.28M</div>
        </div>
      </div>
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Facturas</div>
          <div class="ay-dash-kpi-value" data-ay-claim="kpi-invoice-count">42</div>
        </div>
      </div>
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Promedio</div>
          <div class="ay-dash-kpi-value" data-ay-claim="kpi-avg-ticket">$30K</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

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


def _provenance_item(
    claim_key: str,
    *,
    source_refs=None,
    tool_call_ids=None,
    label: str | None = None,
):
    refs = source_refs or tool_call_ids or ["call_sql_1"]
    return {
        "claim_key": claim_key,
        "label": label or claim_key.replace("-", " ").title(),
        "source_refs": refs,
        "definition": {
            "metric": "SUM(total)",
            "dataset_ref": "embedded:analytics-data",
            "base_filters": "sin filtros de fecha",
        },
        "transformation": "SUM(total)",
    }


def _create_data_access(
    conversation,
    message,
    tool_call_id: str = "call_sql_1",
    source_ref: str = "sql_1",
):
    return DataAccess.objects.create(
        conversation=conversation,
        message=message,
        tool_call_id=tool_call_id,
        source_ref=source_ref,
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT SUM(total) FROM invoice", "purpose": "Total de facturas"},
        response_summary={"row_count": 1, "tables": ["invoice"], "columns": ["total"]},
    )


@pytest.fixture(autouse=True)
def _reset_context():
    reset_agent_context()
    yield
    reset_agent_context()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="claimsuser", password="pass")


@pytest.fixture
def conversation(user):
    conv = Conversation.objects.create(user=user, title="Claims test")
    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content="",
    )
    return conv, message


@pytest.fixture
def workspace_backend():
    backend = DictWorkspaceBackend()
    set_agent_backend(backend)
    return backend


@pytest.mark.django_db
class TestClaimHelpers:
    def test_extract_claim_keys_from_html(self):
        keys = extract_claim_keys_from_html(
            '<div data-ay-claim="kpi-a"></div><span data-ay-claim=\'kpi-b\'></span>'
        )
        assert keys == {"kpi-a", "kpi-b"}

    def test_validate_provenance_payload_rejects_missing_html_key(self, conversation):
        conv, _message = conversation
        html = '<div data-ay-claim="kpi-other">—</div>'
        items = [_provenance_item("kpi-total-revenue")]
        with pytest.raises(ValueError, match="no aparece en el HTML"):
            validate_provenance_payload(conv, html, items)


@pytest.mark.django_db
class TestPublishClaims:
    def test_publish_creates_claims_and_links(self, user, conversation, workspace_backend):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SINGLE_KPI_DASHBOARD_HTML)
        provenance = [_provenance_item("kpi-total-revenue")]

        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                tool_call_id="call_pub_claims",
                provenance=provenance,
            )
        )

        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        manifest = file_obj.content_json["provenance"]
        assert manifest["version"] == 1
        assert "kpi-total-revenue" in manifest["claim_keys"]

        claim = DataClaim.objects.get(
            artifact_file=file_obj,
            claim_key="kpi-total-revenue",
        )
        assert claim.surface == DataClaim.Surface.DASHBOARD_KPI
        assert claim.label == "Kpi Total Revenue"
        assert claim.artifact_version == file_obj.version
        assert manifest["claim_keys"]["kpi-total-revenue"] == str(claim.id)

        link = ProvenanceLink.objects.get(claim=claim)
        assert link.data_access.tool_call_id == "call_sql_1"
        assert link.transformation == "SUM(total)"
        assert link.ordinal == 0

    def test_publish_rejects_unknown_tool_call_id(self, user, conversation, workspace_backend):
        conv, message = conversation
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SINGLE_KPI_DASHBOARD_HTML)

        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                provenance=[_provenance_item("kpi-total-revenue", source_refs=["sql_missing"])],
            )
        )

        assert result["ok"] is False
        assert "sql_missing" in result["error"]
        assert "Disponibles en esta conversación" in result["error"]
        assert DataClaim.objects.count() == 0

    def test_publish_with_source_refs(self, user, conversation, workspace_backend):
        conv, message = conversation
        _create_data_access(conv, message, source_ref="sql_1")
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SINGLE_KPI_DASHBOARD_HTML)
        provenance = [_provenance_item("kpi-total-revenue", source_refs=["sql_1"])]

        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                provenance=provenance,
            )
        )

        assert result["ok"] is True
        link = ProvenanceLink.objects.get(
            claim__artifact_file_id=result["file_id"],
            claim__claim_key="kpi-total-revenue",
        )
        assert link.data_access.source_ref == "sql_1"

    def test_publish_requires_data_ay_claim_in_html(self, user, conversation, workspace_backend):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SINGLE_KPI_DASHBOARD_HTML)

        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                provenance=[_provenance_item("kpi-not-in-html")],
            )
        )

        assert result["ok"] is False
        assert "kpi-not-in-html" in result["error"]
        assert DataClaim.objects.count() == 0

    def test_one_data_access_multiple_claims(self, user, conversation, workspace_backend):
        conv, message = conversation
        data_access = _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, PROVENANCE_DASHBOARD_HTML)
        provenance = [
            _provenance_item("kpi-total-revenue"),
            _provenance_item("kpi-invoice-count", label="Facturas"),
            _provenance_item("kpi-avg-ticket", label="Ticket promedio"),
        ]

        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                provenance=provenance,
            )
        )

        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert DataClaim.objects.filter(artifact_file=file_obj).count() == 3
        links = ProvenanceLink.objects.filter(data_access=data_access)
        assert links.count() == 3
        assert {link.claim.claim_key for link in links} == {
            "kpi-total-revenue",
            "kpi-invoice-count",
            "kpi-avg-ticket",
        }

    def test_republish_updates_claims_in_place(self, user, conversation, workspace_backend):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SINGLE_KPI_DASHBOARD_HTML)
        provenance = [_provenance_item("kpi-total-revenue", label="Ingresos v1")]

        created = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas",
                filename="ventas.html",
                provenance=provenance,
            )
        )
        file_obj = File.objects.get(id=created["file_id"])
        original_claim_id = file_obj.content_json["provenance"]["claim_keys"]["kpi-total-revenue"]
        original_version = file_obj.version

        updated = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas actualizado",
                file_id=str(file_obj.id),
                provenance=[_provenance_item("kpi-total-revenue", label="Ingresos v2")],
            )
        )

        assert updated["ok"] is True
        file_obj.refresh_from_db()
        assert file_obj.version == original_version + 1

        claim = DataClaim.objects.get(id=original_claim_id)
        assert claim.label == "Ingresos v2"
        assert claim.artifact_version == file_obj.version
        assert file_obj.content_json["provenance"]["claim_keys"]["kpi-total-revenue"] == original_claim_id
        assert ProvenanceLink.objects.filter(claim=claim).count() == 1


@pytest.mark.django_db
class TestInlineClaims:
    def _invoke_table(self, source_refs=None, tool_call_ids=None):
        return show_data_table.invoke(
            {
                "type": "tool_call",
                "name": "show_data_table",
                "id": "call_table_1",
                "args": {
                    "columns": ["Región", "Total"],
                    "rows": [["Norte", "$100"]],
                    "caption": "Ventas por región",
                    "source_refs": source_refs,
                    "tool_call_ids": tool_call_ids,
                },
            }
        )

    def _invoke_chart(self, source_refs=None, tool_call_ids=None):
        return show_chart.invoke(
            {
                "type": "tool_call",
                "name": "show_chart",
                "id": "call_chart_1",
                "args": {
                    "chart_type": "bar",
                    "labels": ["Norte"],
                    "series": [{"name": "Ventas", "values": [100]}],
                    "title": "Ventas por región",
                    "source_refs": source_refs,
                    "tool_call_ids": tool_call_ids,
                },
            }
        )

    def test_show_data_table_creates_inline_claim(self, user, conversation):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        result = json.loads(self._invoke_table(source_refs=["sql_1"]).content)
        assert result["ok"] is True

        claim = DataClaim.objects.get(
            conversation=conv,
            message=message,
            claim_key="chat-table-call_table_1",
        )
        assert claim.surface == DataClaim.Surface.CHAT_TABLE
        link = ProvenanceLink.objects.get(claim=claim)
        assert link.data_access.source_ref == "sql_1"

        display = pop_table_display("call_table_1")
        assert display["claim_id"] == str(claim.id)

    def test_show_data_table_accepts_tool_call_ids(self, user, conversation):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        result = json.loads(self._invoke_table(tool_call_ids=["call_sql_1"]).content)
        assert result["ok"] is True

    def test_show_chart_creates_inline_claim(self, user, conversation):
        conv, message = conversation
        _create_data_access(conv, message)
        set_agent_context(conv, user, message=message)

        result = json.loads(self._invoke_chart(tool_call_ids=["call_sql_1"]).content)
        assert result["ok"] is True

        claim = DataClaim.objects.get(
            conversation=conv,
            message=message,
            claim_key="chat-chart-call_chart_1",
        )
        assert claim.surface == DataClaim.Surface.CHAT_CHART

        display = pop_chart_display("call_chart_1")
        assert display["claim_id"] == str(claim.id)

    def test_inline_claim_rejects_unknown_tool_call_id(self, user, conversation):
        conv, message = conversation
        set_agent_context(conv, user, message=message)

        result = json.loads(self._invoke_table(source_refs=["sql_missing"]).content)
        assert result["ok"] is False
        assert "sql_missing" in result["error"]
        assert DataClaim.objects.count() == 0
