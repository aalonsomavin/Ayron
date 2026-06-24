import json

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import set_agent_backend, set_agent_context
from apps.agent.tests.dict_workspace_backend import DictWorkspaceBackend
from apps.agent.tools.chart import render_inline_chart_html, validate_chart_input
from apps.agent.tools.html_report import (
    build_export_html,
    build_preview_fragment,
    infer_html_kind,
    pop_html_report_display,
    run_hydrate_html_artifact,
    run_publish_html_artifact,
    run_validate_html_artifact,
    validate_html_report_content,
)
from apps.agent.tools.html_sanitize import sanitize_html_report
from apps.agent.workspace import draft_artifact_path, write_workspace_file
from apps.chat.models import Conversation
from apps.files.models import File
from apps.files.services import serialize_file_for_ui

User = get_user_model()


SAMPLE_HTML = """
<style>
  .report { font-family: Georgia, serif; max-width: 720px; margin: 0 auto; }
  .report h1 { font-size: 28px; }
</style>
<main class="report">
  <h1>Informe de ventas</h1>
  <p>Las ventas subieron un 12 %.</p>
  <table>
    <thead><tr><th>Región</th><th>Total</th></tr></thead>
    <tbody><tr><td>EMEA</td><td>€100k</td></tr></tbody>
  </table>
  <svg viewBox="0 0 100 50" width="100" height="50"><rect x="10" y="10" width="30" height="30" fill="#3b6ef6"/></svg>
</main>
"""

DASHBOARD_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas Mayo</h1>
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Ingresos</div>
          <div class="ay-dash-kpi-value">$1.28M</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

DASHBOARD_SHELL = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas Mayo</h1>
    <div class="ay-dash-grid"></div>
  </div>
</div>
"""

KPI_BLOCK = """
<div class="ay-dash-col ay-dash-col--3">
  <div class="ay-dash-card">
    <div class="ay-dash-kpi-label">Ingresos</div>
    <div class="ay-dash-kpi-value">$1.28M</div>
  </div>
</div>
"""

INTERACTIVE_DASHBOARD_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas</h1>
    <div class="ay-dash-filter-bar">
      <script type="application/json">
      {"filters":[{"id":"region","label":"Región","options":["Todas","Norte"],"target":"#t1","attr":"data-region"}]}
      </script>
    </div>
    <div class="ay-dash-tabs">
      <div class="ay-dash-tab-panels">
        <div class="ay-dash-tab-panel" data-page="a" data-label="A">
          <table id="t1" class="ay-dash-table ay-dash-table--sortable">
            <thead><tr><th>Región</th></tr></thead>
            <tbody><tr data-region="Norte"><td>Norte</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
"""

ANALYTICS_DASHBOARD_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Facturación</h1>
    <div class="ay-dash-filter-scope">
      <script type="application/json" id="analytics-data">
      {"rows":[{"year":2009,"country":"USA","genre":"Rock","amount":12.5,"invoice_id":"INV-1"},{"year":2010,"country":"Canada","genre":"Rock","amount":6.1,"invoice_id":"INV-2"}]}
      </script>
      <script type="application/json">
      {"slicers":[{"id":"year","field":"year","label":"Año","control":"pills"},{"id":"country","field":"country","label":"País","control":"dropdown"}]}
      </script>
      <div class="ay-dash-slicer-bar"></div>
      <div class="ay-dash-filter-chips"></div>
      <div class="ay-dash-grid">
        <div class="ay-dash-col ay-dash-col--3">
          <div class="ay-dash-card ay-dash-kpi-live" data-agg="sum:amount" data-format="currency">
            <div class="ay-dash-kpi-label">Total</div>
            <div class="ay-dash-kpi-value">—</div>
          </div>
        </div>
        <div class="ay-dash-col ay-dash-col--6">
          <div class="ay-chart ay-chart--live" data-chart-id="chart-country" data-dimension="country" data-measure="sum:amount" data-cross-filter="country">
            <script id="chart-country" type="application/json">
            {"chart_type":"bar","title":"Por país","datasets":[{"label":"Importe","color_index":0}],"value_format":"currency"}
            </script>
            <div class="ay-chart__card">
              <div class="ay-chart__title">Por país</div>
              <div class="ay-chart__plot"><canvas class="ay-chart__canvas"></canvas></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

SECTION_TABS_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas</h1>
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--12">
        <div class="ay-dash-tab-scope">
          <div class="ay-dash-card ay-dash-card--flush">
            <div class="ay-dash-card-header ay-dash-card-header--with-tabs">
              <span class="ay-dash-card-header__title">Por región</span>
              <div class="ay-dash-tabs ay-dash-tabs--header" data-panels-target="#region-panels"></div>
            </div>
          </div>
          <div id="region-panels" class="ay-dash-tab-panels">
            <div class="ay-dash-tab-panel" data-page="norte" data-label="Norte">
              <div class="ay-dash-card"><div class="ay-dash-kpi-value">€120K</div></div>
            </div>
            <div class="ay-dash-tab-panel" data-page="sur" data-label="Sur">
              <div class="ay-dash-card"><div class="ay-dash-kpi-value">€98K</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

NESTED_TABS_SHELL = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--12">
        <div class="ay-dash-tabs ay-dash-tabs--section">
          <div class="ay-dash-tab-panels">
            <div class="ay-dash-tab-panel" data-page="2009" data-label="2009"></div>
          </div>
        </div>
      </div>
    </div>
    <div class="ay-dash-tabs">
      <div class="ay-dash-tab-panels">
        <div class="ay-dash-tab-panel" data-page="resumen" data-label="Resumen"></div>
      </div>
    </div>
  </div>
</div>
"""

PAGE_TAB_PANEL = """
<div class="ay-dash-tab-panel" data-page="artistas" data-label="Artistas"></div>
"""

CALCULATOR_HTML = """
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Simulador</h1>
    <div class="ay-dash-calculator">
      <script type="application/json">
      {"inputs":[{"id":"units","label":"Unidades","type":"number","default":1000,"min":0},{"id":"price","label":"Precio","type":"number","default":42.5,"min":0}],"constants":{"fixed_cost":30000},"outputs":[{"id":"revenue","label":"Ingresos","expr":"units * price","format":"currency"}]}
      </script>
      <div class="ay-dash-grid">
        <div class="ay-dash-col ay-dash-col--3" data-calc-input="units">
          <div class="ay-dash-card"></div>
        </div>
        <div class="ay-dash-col ay-dash-col--3" data-calc-input="price">
          <div class="ay-dash-card"></div>
        </div>
        <div class="ay-dash-col ay-dash-col--3" data-calc-output="revenue">
          <div class="ay-dash-card">
            <div class="ay-dash-kpi-label">Ingresos</div>
            <div class="ay-dash-kpi-value ay-dash-kpi-value--calc">—</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

CALCULATOR_BLOCK = """
<div class="ay-dash-col ay-dash-col--12">
  <div class="ay-dash-calculator">
    <script type="application/json">
    {"inputs":[{"id":"units","label":"Unidades","type":"number","default":500,"min":0},{"id":"price","label":"Precio","type":"number","default":10,"min":0}],"outputs":[{"id":"revenue","expr":"units * price","format":"currency"}]}
    </script>
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--3" data-calc-input="units"><div class="ay-dash-card"></div></div>
      <div class="ay-dash-col ay-dash-col--3" data-calc-output="revenue">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Ingresos</div>
          <div class="ay-dash-kpi-value ay-dash-kpi-value--calc">—</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def _chart_report_html() -> str:
    chart = render_inline_chart_html(
        validate_chart_input(
            chart_type="bar",
            labels=["EMEA", "APAC"],
            series=[{"name": "Ingresos", "values": [100, 200]}],
            title="Por región",
        ),
        chart_id="chart-report",
    )
    return f"""
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas</h1>
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--12">{chart}</div>
    </div>
  </div>
</div>
"""


@pytest.fixture
def user(db):
    return User.objects.create_user(username="htmluser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.fixture
def workspace_backend():
    backend = DictWorkspaceBackend()
    set_agent_backend(backend)
    return backend


@pytest.mark.django_db
class TestHtmlReportTool:
    def test_sanitize_preserves_inline_script(self):
        dirty = "<p>Hola</p><script>window.__ok = true</script>"
        clean = sanitize_html_report(dirty)
        assert "Hola" in clean
        assert "window.__ok" in clean

    def test_sanitize_strips_disallowed_external_script(self):
        dirty = '<p>Hola</p><script src="https://evil.example/hack.js"></script>'
        clean = sanitize_html_report(dirty)
        assert "Hola" in clean
        assert "evil.example" not in clean

    def test_sanitize_preserves_chart_json_script(self):
        dirty = """
        <div class="ay-chart" data-chart-id="chart-1">
          <script id="chart-1" type="application/json">{"chart_type":"bar","labels":["A"],"datasets":[{"label":"S","data":[1],"color_index":0}],"value_format":"number"}</script>
          <canvas class="ay-chart__canvas"></canvas>
        </div>
        """
        clean = sanitize_html_report(dirty)
        assert 'type="application/json"' in clean
        assert "chart-1" in clean
        assert "ay-chart__canvas" in clean
        assert "alert" not in clean

    def test_validate_html_report_content(self):
        result = validate_html_report_content("Informe", SAMPLE_HTML, "Mayo 2026")
        assert result["format"] == "html"
        assert result["html_kind"] == "report"
        assert result["status"] == "published"
        assert "Informe de ventas" in result["body_html"]
        assert result["full_document"] is False

    def test_validate_html_kind_dashboard(self):
        result = validate_html_report_content("Ventas", DASHBOARD_HTML, "")
        assert result["html_kind"] == "dashboard"

    def test_validate_html_kind_explicit_match(self):
        result = validate_html_report_content(
            "Ventas", DASHBOARD_HTML, "", html_kind="dashboard"
        )
        assert result["html_kind"] == "dashboard"

    def test_validate_html_kind_mismatch_raises(self):
        with pytest.raises(ValueError, match="does not match markup"):
            validate_html_report_content(
                "Ventas", DASHBOARD_HTML, "", html_kind="report"
            )

    def test_infer_html_kind(self):
        assert infer_html_kind(DASHBOARD_HTML) == "dashboard"
        assert infer_html_kind(SAMPLE_HTML) == "report"

    def test_build_preview_fragment(self):
        content = validate_html_report_content("Informe", SAMPLE_HTML, "")
        html = build_preview_fragment(content)
        assert "<!DOCTYPE html>" in html
        assert "ay-html-report-preview" in html
        assert "fonts.googleapis.com" in html
        assert ".ay-dash-page" in html or "ay-dash-page" in html
        assert ".ay-report-prose" in html or "ay-report-prose" in html
        assert "<table>" in html
        assert "<svg" in html

    def test_build_preview_fragment_dashboard(self):
        content = validate_html_report_content("Ventas", DASHBOARD_HTML, "")
        html = build_preview_fragment(content)
        assert "ay-dash-kpi-value" in html
        assert "ay-dash-page" in html

    def test_build_export_html(self):
        content = validate_html_report_content("Informe", SAMPLE_HTML, "")
        html = build_export_html(content)
        assert "<!DOCTYPE html>" in html
        assert "<style>" in html
        assert "fonts.googleapis.com" in html
        assert ".ay-dash-" in html
        assert ".ay-report-prose" in html
        assert "<table>" in html
        assert "<svg" in html
        assert "AyronChart.mountAll" not in html
        assert "AyronDashboard.mountAll" not in html
        assert "Generado con Ayron" in html

    def test_build_export_html_dashboard(self):
        content = validate_html_report_content("Ventas", DASHBOARD_HTML, "")
        html = build_export_html(content)
        assert ".ay-dash-page" in html
        assert ".ay-dash-kpi-value" in html
        assert "fonts.googleapis.com" in html
        assert 'class="ay-dash-page"' in html

    def test_build_export_html_with_chart(self):
        html_with_chart = """
<div class="ay-dash-page"><div class="ay-dash-inner">
<canvas id="c1"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>new Chart(document.getElementById("c1"), { type: "bar", data: { labels: ["A"], datasets: [{ data: [1] }] } });</script>
</div></div>
"""
        content = validate_html_report_content("Ventas", html_with_chart, "")
        html = build_export_html(content)
        assert "chart.js" in html
        assert "new Chart" in html
        assert "AyronChart.mountAll" not in html

    def test_build_preview_fragment_with_chart(self):
        html_with_chart = """
<div class="ay-dash-page"><canvas id="c1"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>new Chart(document.getElementById("c1"), { type: "bar", data: { labels: ["A"], datasets: [{ data: [1] }] } });</script>
</div>
"""
        content = validate_html_report_content("Ventas", html_with_chart, "")
        html = build_preview_fragment(content)
        assert "<!DOCTYPE html>" in html
        assert "chart.js" in html
        assert "new Chart" in html

    def test_build_export_html_with_interactive_dashboard(self):
        content = validate_html_report_content("Ventas", INTERACTIVE_DASHBOARD_HTML, "")
        html = build_export_html(content)
        assert "ay-dash-filter-bar" in html
        assert "AyronDashboard.mountAll" not in html

    def test_sanitize_analytics_filter_scope(self):
        clean = sanitize_html_report(ANALYTICS_DASHBOARD_HTML)
        assert "ay-dash-filter-scope" in clean
        assert "data-agg" in clean
        assert "data-dimension" in clean
        assert "data-measure" in clean
        assert "data-cross-filter" in clean
        assert "ay-chart--live" in clean
        assert 'type="application/json"' in clean

    def test_build_export_html_with_analytics_scope(self):
        content = validate_html_report_content("Facturación", ANALYTICS_DASHBOARD_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" not in html
        assert "AyronChart.mountAll" not in html
        assert "ay-dash-filter-scope" in html
        assert 'type="application/json"' in html

    def test_sanitize_section_tabs_with_external_panels(self):
        clean = sanitize_html_report(SECTION_TABS_HTML)
        assert "data-panels-target" in clean
        assert "ay-dash-tabs--header" in clean
        assert "ay-dash-tab-scope" in clean

    def test_build_export_html_with_section_tabs(self):
        content = validate_html_report_content("Ventas", SECTION_TABS_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" not in html
        assert "data-panels-target" in html

    def test_sanitize_calculator_block(self):
        clean = sanitize_html_report(CALCULATOR_HTML)
        assert "ay-dash-calculator" in clean
        assert "data-calc-output" in clean
        assert "data-calc-input" in clean
        assert 'type="application/json"' in clean

    def test_sanitize_preserves_agent_input(self):
        dirty = '<div class="ay-dash-calculator"><input type="number" value="1"></div>'
        clean = sanitize_html_report(dirty)
        assert "<input" in clean

    def test_build_export_html_with_calculator(self):
        content = validate_html_report_content("Simulador", CALCULATOR_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" not in html
        assert "ay-dash-calculator" in html

    def test_publish_html_artifact_creates_report(self, user, conversation, workspace_backend):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SAMPLE_HTML)
        result = json.loads(
            run_publish_html_artifact(
                path,
                "Informe de ventas",
                subtitle="Mayo 2026",
                filename="ventas-mayo.html",
                tool_call_id="call_pub_1",
            )
        )
        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.mime_type == "text/html"
        assert file_obj.content_json["html_kind"] == "report"
        assert "Informe de ventas" in file_obj.content_json["body_html"]
        display = pop_html_report_display("call_pub_1")
        assert display["updated"] is False

    def test_publish_html_artifact_creates_dashboard(self, user, conversation, workspace_backend):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, DASHBOARD_HTML)
        result = json.loads(
            run_publish_html_artifact(
                path,
                "Ventas Mayo",
                filename="ventas-mayo.html",
                tool_call_id="call_pub_dash",
            )
        )
        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.content_json["html_kind"] == "dashboard"
        ui = serialize_file_for_ui(file_obj)
        assert ui["meta"] == "Dashboard"
        assert ui["open_expanded"] is True

    def test_validate_html_artifact_tool(self, user, conversation, workspace_backend):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(
            workspace_backend,
            path,
            '<div class="ay-dash-page"><script>window.__dash = 1</script><p>ok</p></div>',
        )
        result = json.loads(run_validate_html_artifact(path))
        assert result["ok"] is True
        assert result["html_kind"] == "dashboard"
        cleaned = workspace_backend.files[path]
        assert "window.__dash" in cleaned
        assert "ay-dash-page" in cleaned

    def test_hydrate_and_update_html_artifact(self, user, conversation, workspace_backend):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SAMPLE_HTML)
        created = json.loads(
            run_publish_html_artifact(
                path,
                "Informe",
                filename="informe.html",
                tool_call_id="call_pub_2",
            )
        )
        hydrated = json.loads(run_hydrate_html_artifact(created["file_id"]))
        assert hydrated["ok"] is True
        assert hydrated["path"].endswith(f"{created['file_id']}.html")

        updated_html = SAMPLE_HTML.replace("12 %", "18 %")
        write_workspace_file(workspace_backend, hydrated["path"], updated_html)
        updated = json.loads(
            run_publish_html_artifact(
                hydrated["path"],
                "Informe actualizado",
                file_id=created["file_id"],
                tool_call_id="call_pub_3",
            )
        )
        assert updated["ok"] is True
        assert updated["version"] == 2
        file_obj = File.objects.get(id=created["file_id"])
        assert "18 %" in file_obj.content_json["body_html"]

    def test_publish_wrong_conversation(self, user, conversation, workspace_backend):
        other = Conversation.objects.create(user=user)
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, SAMPLE_HTML)
        created = json.loads(
            run_publish_html_artifact(
                path,
                "Informe",
                filename="informe.html",
                tool_call_id="call_pub_4",
            )
        )
        set_agent_context(other, user)
        result = json.loads(
            run_publish_html_artifact(
                path,
                "Hack",
                file_id=created["file_id"],
                tool_call_id="call_pub_5",
            )
        )
        assert result["ok"] is False

    def test_publish_html_artifact_sanitizes_malformed_filename(self, user, conversation, workspace_backend):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, DASHBOARD_HTML)
        corrupted_filename = (
            "brecha-precio-vs-volumen-mexar.html'}] "
            "【analysis to=functions.publish_html_artifact malformed JSON"
        )
        result = json.loads(
            run_publish_html_artifact(
                path,
                "Brecha de precio vs volumen vendido",
                filename=corrupted_filename,
                tool_call_id="call_pub_malformed",
            )
        )
        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.original_name == "brecha-precio-vs-volumen-mexar.html"
        display = pop_html_report_display("call_pub_malformed")
        assert display["name"] == "brecha-precio-vs-volumen-mexar"

    def test_publish_html_artifact_update_sanitizes_existing_corrupted_name(
        self, user, conversation, workspace_backend
    ):
        set_agent_context(conversation, user)
        path = draft_artifact_path()
        write_workspace_file(workspace_backend, path, DASHBOARD_HTML)
        created = json.loads(
            run_publish_html_artifact(
                path,
                "Brecha de precio vs volumen vendido",
                filename="brecha-precio-vs-volumen-mexar.html",
                tool_call_id="call_pub_create",
            )
        )
        file_obj = File.objects.get(id=created["file_id"])
        file_obj.original_name = (
            "brecha-precio-vs-volumen-mexar.html'}] "
            "【analysis to=functions.publish_html_artifact malformed JSON"
        )
        file_obj.save(update_fields=["original_name"])

        updated = json.loads(
            run_publish_html_artifact(
                path,
                "Brecha de precio vs volumen vendido",
                file_id=created["file_id"],
                tool_call_id="call_pub_update",
            )
        )
        assert updated["ok"] is True
        file_obj.refresh_from_db()
        assert file_obj.original_name == "brecha-precio-vs-volumen-mexar.html"
        display = pop_html_report_display("call_pub_update")
        assert display["name"] == "brecha-precio-vs-volumen-mexar"
