import json

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import set_agent_context
from apps.agent.tools.html_report import (
    build_export_html,
    build_preview_fragment,
    create_html_report,
    get_html_report,
    update_html_report,
    validate_html_report_content,
)
from apps.agent.tools.html_sanitize import sanitize_html_report
from apps.chat.models import Conversation
from apps.files.models import File

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
        assert "script" not in clean

    def test_validate_html_report_content(self):
        result = validate_html_report_content("Informe", SAMPLE_HTML, "Mayo 2026")
        assert result["format"] == "html"
        assert "Informe de ventas" in result["body_html"]
        assert result["full_document"] is False

    def test_build_preview_fragment(self):
        content = validate_html_report_content("Informe", SAMPLE_HTML, "")
        html = build_preview_fragment(content)
        assert "ay-html-report-preview" in html
        assert "<table>" in html
        assert "<svg" in html

    def test_build_export_html(self):
        content = validate_html_report_content("Informe", SAMPLE_HTML, "")
        html = build_export_html(content)
        assert "<!DOCTYPE html>" in html
        assert "<style>" in html
        assert "<table>" in html
        assert "<svg" in html
        assert "<script" not in html
        assert "Generado con Ayron" in html

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
        assert "Informe de ventas" in file_obj.content_json["body_html"]

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
