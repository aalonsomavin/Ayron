import json

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import set_agent_context
from apps.agent.tools.chart import render_inline_chart_html, validate_chart_input
from apps.agent.tools.html_report import (
    append_html_report_block,
    append_to_container,
    build_export_html,
    build_preview_fragment,
    create_html_report,
    get_html_report,
    infer_html_kind,
    pop_html_report_display,
    publish_html_report,
    update_html_report,
    validate_html_report_content,
)
from apps.agent.tools.html_sanitize import sanitize_html_report
from apps.chat.models import Conversation
from apps.files.models import File
from apps.files.services import serialize_file_for_ui

User = get_user_model()


def invoke_tool(tool, tool_call_id, **kwargs):
    result = tool.invoke(
        {
            "type": "tool_call",
            "name": tool.name,
            "id": tool_call_id,
            "args": kwargs,
        }
    )
    return result.content if hasattr(result, "content") else result


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


@pytest.mark.django_db
class TestHtmlReportTool:
    def test_sanitize_strips_script(self):
        dirty = "<p>Hola</p><script>alert(1)</script>"
        clean = sanitize_html_report(dirty)
        assert "Hola" in clean
        assert "alert" not in clean

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
        assert "<script" not in html
        assert "Generado con Ayron" in html

    def test_build_export_html_dashboard(self):
        content = validate_html_report_content("Ventas", DASHBOARD_HTML, "")
        html = build_export_html(content)
        assert ".ay-dash-page" in html
        assert ".ay-dash-kpi-value" in html
        assert "fonts.googleapis.com" in html
        assert 'class="ay-dash-page"' in html

    def test_build_export_html_with_chart(self):
        content = validate_html_report_content("Ventas", _chart_report_html(), "")
        html = build_export_html(content)
        assert ".ay-chart__plot" in html
        assert "chart.js" in html
        assert "AyronChart.mountAll" in html
        assert 'type="application/json"' in html

    def test_build_preview_fragment_with_chart(self):
        content = validate_html_report_content("Ventas", _chart_report_html(), "")
        html = build_preview_fragment(content)
        assert ".ay-chart__plot" in html
        assert "chart.js" not in html

    def test_create_html_report(self, user, conversation):
        set_agent_context(conversation, user)
        result = json.loads(
            invoke_tool(
                create_html_report,
                "call_html_1",
                title="Informe de ventas",
                subtitle="Mayo 2026",
                html=SAMPLE_HTML,
                filename="ventas-mayo.html",
            )
        )
        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.mime_type == "text/html"
        assert file_obj.content_json["html_kind"] == "report"
        assert "Informe de ventas" in file_obj.content_json["body_html"]

    def test_create_dashboard_html_report(self, user, conversation):
        set_agent_context(conversation, user)
        result = json.loads(
            invoke_tool(
                create_html_report,
                "call_html_dash",
                title="Ventas Mayo",
                html=DASHBOARD_HTML,
            )
        )
        assert result["ok"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.content_json["html_kind"] == "dashboard"
        ui = serialize_file_for_ui(file_obj)
        assert ui["meta"] == "Dashboard"
        assert ui["open_expanded"] is True

    def test_create_report_open_expanded_false(self, user, conversation):
        set_agent_context(conversation, user)
        result = json.loads(
            invoke_tool(
                create_html_report,
                "call_html_rep",
                title="Informe",
                html=SAMPLE_HTML,
            )
        )
        file_obj = File.objects.get(id=result["file_id"])
        ui = serialize_file_for_ui(file_obj)
        assert ui["meta"] == "Report · HTML"
        assert ui["open_expanded"] is False

    def test_build_export_html_with_interactive_dashboard(self):
        content = validate_html_report_content("Ventas", INTERACTIVE_DASHBOARD_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" in html
        assert "ay-dash-filter-bar" in html

    def test_sanitize_section_tabs_with_external_panels(self):
        clean = sanitize_html_report(SECTION_TABS_HTML)
        assert "data-panels-target" in clean
        assert "ay-dash-tabs--header" in clean
        assert "ay-dash-tab-scope" in clean

    def test_build_export_html_with_section_tabs(self):
        content = validate_html_report_content("Ventas", SECTION_TABS_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" in html
        assert "data-panels-target" in html

    def test_sanitize_calculator_block(self):
        clean = sanitize_html_report(CALCULATOR_HTML)
        assert "ay-dash-calculator" in clean
        assert "data-calc-output" in clean
        assert "data-calc-input" in clean
        assert 'type="application/json"' in clean

    def test_sanitize_strips_agent_input(self):
        dirty = '<div class="ay-dash-calculator"><input type="number" value="1"></div>'
        clean = sanitize_html_report(dirty)
        assert "<input" not in clean

    def test_build_export_html_with_calculator(self):
        content = validate_html_report_content("Simulador", CALCULATOR_HTML, "")
        html = build_export_html(content)
        assert "AyronDashboard.mountAll" in html
        assert "ay-dash-calculator" in html

    def test_incremental_append_calculator_block(self, user, conversation):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_html_report,
                "call_calc_1",
                title="Simulador",
                html=DASHBOARD_SHELL,
                build_mode="incremental",
                html_kind="dashboard",
            )
        )
        appended = json.loads(
            invoke_tool(
                append_html_report_block,
                "call_calc_2",
                file_id=created["file_id"],
                html=CALCULATOR_BLOCK,
                target="grid",
            )
        )
        assert appended["ok"] is True
        file_obj = File.objects.get(id=created["file_id"])
        assert "ay-dash-calculator" in file_obj.content_json["body_html"]

        published = json.loads(
            invoke_tool(
                publish_html_report,
                "call_calc_3",
                file_id=created["file_id"],
            )
        )
        assert published["ok"] is True
        file_obj.refresh_from_db()
        assert file_obj.content_json["status"] == "published"

    def test_append_to_container(self):
        updated = append_to_container(DASHBOARD_SHELL, "ay-dash-grid", KPI_BLOCK)
        assert updated.count("ay-dash-kpi-value") == 1
        assert "ay-dash-grid" in updated

    def test_append_tabs_targets_page_level_not_section(self):
        updated = append_to_container(NESTED_TABS_SHELL, "ay-dash-tab-panels", PAGE_TAB_PANEL)
        assert updated.count('data-page="artistas"') == 1
        assert updated.count('data-page="2009"') == 1
        assert updated.index('data-page="artistas"') > updated.index('data-page="resumen"')
        assert updated.index('data-page="2009"') < updated.index('data-page="resumen"')

    def test_mount_tabs_uses_direct_child_panels_only(self):
        from django.conf import settings

        content = (settings.BASE_DIR / "static" / "js" / "ayron-dashboard.js").read_text(
            encoding="utf-8"
        )
        assert ":scope > .ay-dash-tab-panel[data-page]" in content

    def test_create_incremental_dashboard_draft(self, user, conversation):
        set_agent_context(conversation, user)
        result = json.loads(
            invoke_tool(
                create_html_report,
                "call_inc_1",
                title="Ventas Mayo",
                html=DASHBOARD_SHELL,
                build_mode="incremental",
                html_kind="dashboard",
            )
        )
        assert result["ok"] is True
        assert result["draft"] is True
        file_obj = File.objects.get(id=result["file_id"])
        assert file_obj.content_json["status"] == "draft"
        display = pop_html_report_display("call_inc_1")
        assert display["skip_chat_event"] is True

    def test_incremental_append_and_publish(self, user, conversation):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_html_report,
                "call_inc_2",
                title="Ventas Mayo",
                html=DASHBOARD_SHELL,
                build_mode="incremental",
                html_kind="dashboard",
            )
        )
        appended = json.loads(
            invoke_tool(
                append_html_report_block,
                "call_inc_3",
                file_id=created["file_id"],
                html=KPI_BLOCK,
                target="grid",
            )
        )
        assert appended["ok"] is True
        assert appended["draft"] is True
        file_obj = File.objects.get(id=created["file_id"])
        assert "ay-dash-kpi-value" in file_obj.content_json["body_html"]
        assert file_obj.version == 2

        published = json.loads(
            invoke_tool(
                publish_html_report,
                "call_inc_4",
                file_id=created["file_id"],
            )
        )
        assert published["ok"] is True
        assert published.get("draft") is not True
        file_obj.refresh_from_db()
        assert file_obj.content_json["status"] == "published"
        display = pop_html_report_display("call_inc_4")
        assert display.get("skip_chat_event") is not True
        assert display["updated"] is False

    def test_append_rejects_published_file(self, user, conversation):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_html_report,
                "call_inc_5",
                title="Ventas",
                html=DASHBOARD_HTML,
            )
        )
        result = json.loads(
            invoke_tool(
                append_html_report_block,
                "call_inc_6",
                file_id=created["file_id"],
                html=KPI_BLOCK,
            )
        )
        assert result["ok"] is False

    def test_get_and_update_html_report(self, user, conversation):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_html_report,
                "call_html_2",
                title="Informe",
                html=SAMPLE_HTML,
            )
        )
        fetched = json.loads(get_html_report.invoke({"file_id": created["file_id"]}))
        assert fetched["ok"] is True
        assert fetched["html_kind"] == "report"
        assert "Informe de ventas" in fetched["html"]

        updated_html = SAMPLE_HTML.replace("12 %", "18 %")
        updated = json.loads(
            invoke_tool(
                update_html_report,
                "call_html_3",
                file_id=created["file_id"],
                title="Informe actualizado",
                html=updated_html,
            )
        )
        assert updated["ok"] is True
        assert updated["version"] == 2

    def test_update_wrong_conversation(self, user, conversation):
        other = Conversation.objects.create(user=user)
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_html_report,
                "call_html_4",
                title="Informe",
                html=SAMPLE_HTML,
            )
        )
        set_agent_context(other, user)
        result = json.loads(
            invoke_tool(
                update_html_report,
                "call_html_5",
                file_id=created["file_id"],
                title="Hack",
            )
        )
        assert result["ok"] is False
