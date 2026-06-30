"""
Plan E integration tests + manual E2E checklist:

1. Publish a dashboard with provenance[] and data-ay-claim on KPIs.
2. Save it in Analíticas.
3. Open the dashboard detail view.
4. Click a KPI → side panel shows definition, SQL, and source.
5. Use Copiar to copy SQL.
6. Legacy dashboard without claims → no interactive KPI styling / no panel data.
"""

import pytest
from django.urls import reverse

from apps.agent.tools.html_provenance import inject_provenance_bridge
from apps.chat.models import Conversation, Message
from apps.files.services import save_dashboard
from apps.integrations.models import Integration
from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="planeuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.fixture
def dashboard_with_claim(user, conversation):
    from apps.files.models import HTML_MIME
    from apps.files.services import save_generated_file

    dashboard_html = """
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
    content = {
        "format": "html",
        "html_kind": "dashboard",
        "title": "Ventas",
        "subtitle": "",
        "html": dashboard_html,
        "body_html": dashboard_html,
        "full_document": False,
        "provenance": {
            "version": 1,
            "claim_keys": {"kpi-total-revenue": "00000000-0000-0000-0000-000000000001"},
        },
    }
    preview = inject_provenance_bridge(
        f"<!DOCTYPE html><html><body>{dashboard_html}</body></html>",
        "00000000-0000-0000-0000-000000000099",
    )
    file_obj = save_generated_file(
        conversation=conversation,
        user=user,
        original_name="Ventas.html",
        content_json=content,
        file_bytes=preview.encode("utf-8"),
        preview_html=preview,
        mime_type=HTML_MIME,
    )

    integration = Integration.objects.create(
        slug="plan-e-test",
        name="Mexar Pharma — Producción",
        type=Integration.Type.POSTGRES,
        config={"display": {"status": "connected", "status_label": "Conectada"}},
    )
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="",
    )
    data_access = DataAccess.objects.create(
        conversation=conversation,
        message=message,
        integration=integration,
        tool_call_id="call_plan_e",
        access_kind=DataAccess.AccessKind.SQL,
        request={"sql": "SELECT SUM(total) FROM invoice"},
        response_summary={
            "tables": ["invoice"],
            "columns": ["total"],
            "row_count": 10,
            "truncated": False,
        },
    )
    claim = DataClaim.objects.create(
        conversation=conversation,
        artifact_file=file_obj,
        claim_key="kpi-total-revenue",
        surface=DataClaim.Surface.DASHBOARD_KPI,
        label="Ingresos totales",
        definition={"metric": "SUM(total)"},
    )
    ProvenanceLink.objects.create(
        claim=claim,
        data_access=data_access,
        transformation="SUM(total)",
        ordinal=0,
    )
    content["provenance"]["claim_keys"]["kpi-total-revenue"] = str(claim.id)
    file_obj.content_json = content
    file_obj.save(update_fields=["content_json"])
    return file_obj


@pytest.mark.django_db
class TestDashboardProvenanceUi:
    def test_detail_view_includes_provenance_panel(self, client, user, dashboard_with_claim):
        save_dashboard(user, dashboard_with_claim)
        client.force_login(user)
        response = client.get(
            reverse("dashboards:detail", kwargs={"file_id": dashboard_with_claim.id})
        )
        content = response.content.decode()
        assert response.status_code == 200
        assert 'id="ay-provenance-panel"' in content
        assert 'data-file-id="' in content
        assert "Procedencia del dato" in content

    def test_preview_iframe_points_to_file_preview(self, client, user, dashboard_with_claim):
        save_dashboard(user, dashboard_with_claim)
        client.force_login(user)
        response = client.get(
            reverse("dashboards:preview", kwargs={"file_id": dashboard_with_claim.id})
        )
        content = response.content.decode()
        assert response.status_code == 200
        assert f'/files/{dashboard_with_claim.id}/preview/' in content

    def test_file_preview_injects_provenance_bridge(self, client, user, dashboard_with_claim):
        save_dashboard(user, dashboard_with_claim)
        client.force_login(user)
        response = client.get(
            reverse("files:preview", kwargs={"file_id": dashboard_with_claim.id})
        )
        content = response.content.decode()
        assert response.status_code == 200
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert "ayron:provenance-open" in content
        assert str(dashboard_with_claim.id) in content

    def test_claim_api_usable_from_dashboard(self, client, user, dashboard_with_claim):
        save_dashboard(user, dashboard_with_claim)
        client.force_login(user)
        response = client.get(
            reverse(
                "provenance:file_claim_detail",
                kwargs={
                    "file_id": dashboard_with_claim.id,
                    "claim_key": "kpi-total-revenue",
                },
            )
        )
        payload = response.json()
        assert response.status_code == 200
        assert payload["claim"]["claim_key"] == "kpi-total-revenue"
        assert payload["data_accesses"][0]["sql"] == "SELECT SUM(total) FROM invoice"
