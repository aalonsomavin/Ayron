import pytest
from django.contrib.auth import get_user_model

from apps.chat.models import Conversation
from apps.files.models import File
from apps.files.parsers import parse_upload
from apps.files.services import (
    format_agent_file_index_block,
    format_user_attachments_block,
    get_agent_file_index,
    hydrate_file_payload_for_ui,
    is_dashboard_saved,
    list_saved_dashboards,
    normalize_file_payload_for_ui,
    open_file_stream,
    rename_dashboard_file,
    save_dashboard,
    save_generated_file,
    save_uploaded_file,
    serialize_file_for_ui,
    serialize_saved_dashboard,
    set_dashboard_pinned,
    unsave_dashboard,
    update_generated_file,
    _normalize_html_filename,
)
from apps.files.tests.test_parsers_xlsx import build_sample_xlsx_bytes

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="fileuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.mark.django_db
class TestFileServices:
    def test_save_generated_file(self, user, conversation):
        content = {
            "title": "Informe",
            "subtitle": "Q2",
            "sections": [{"heading": "Resumen", "paragraphs": ["Hola"], "bullets": [], "table": None}],
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Informe.docx",
            content_json=content,
            file_bytes=b"fake-docx",
            preview_html="<div>preview</div>",
        )
        assert File.objects.count() == 1
        assert file_obj.conversation == conversation
        assert file_obj.uploaded_by == user
        assert file_obj.version == 1
        assert file_obj.content_json["role"] == "deliverable"
        assert file_obj.content_json["source"] == "generated"
        assert file_obj.file.name.endswith(".docx")

    def test_update_generated_file_increments_version(self, user, conversation):
        content = {
            "title": "Informe",
            "subtitle": "",
            "sections": [{"heading": "A", "paragraphs": ["v1"], "bullets": [], "table": None}],
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Informe.docx",
            content_json=content,
            file_bytes=b"v1",
            preview_html="<div>v1</div>",
        )
        updated = update_generated_file(
            file_obj=file_obj,
            content_json={
                "title": "Informe v2",
                "subtitle": "",
                "sections": [{"heading": "A", "paragraphs": ["v2"], "bullets": [], "table": None}],
            },
            file_bytes=b"v2",
            preview_html="<div>v2</div>",
        )
        assert updated.version == 2
        assert updated.content_json["title"] == "Informe v2"

    def test_get_agent_file_index(self, user, conversation):
        content = {
            "title": "Doc",
            "subtitle": "",
            "sections": [{"heading": "S", "paragraphs": [], "bullets": [], "table": None}],
        }
        save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Doc.docx",
            content_json=content,
            file_bytes=b"x",
            preview_html="",
        )
        index = get_agent_file_index(conversation)
        assert len(index) == 1
        assert index[0]["name"] == "Doc.docx"

    def test_format_agent_file_index_block(self, user, conversation):
        content = {
            "title": "Doc",
            "subtitle": "",
            "sections": [{"heading": "S", "paragraphs": [], "bullets": [], "table": None}],
        }
        save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Doc.docx",
            content_json=content,
            file_bytes=b"x",
            preview_html="",
        )
        block = format_agent_file_index_block(conversation)
        assert "Archivos generados por el agente" in block
        assert "file_id=" in block
        assert "get_spreadsheet" in block

    def test_save_uploaded_file(self, user, conversation):
        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        file_bytes = build_sample_xlsx_bytes()
        file_obj = save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=file_bytes,
            parsed=parsed,
        )
        assert file_obj.content_json["source"] == "upload"
        assert file_obj.content_json["role"] == "context"
        assert file_obj.format_key == "xlsx"
        assert file_obj.file.name.endswith(".xlsx")
        data = serialize_file_for_ui(file_obj, user=user)
        assert data["role"] == "context"

    def test_format_agent_file_index_block_split_sections(self, user, conversation):
        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=build_sample_xlsx_bytes(),
            parsed=parsed,
        )
        save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Informe.docx",
            content_json={
                "title": "Informe",
                "subtitle": "",
                "sections": [{"heading": "S", "paragraphs": [], "bullets": [], "table": None}],
            },
            file_bytes=b"x",
            preview_html="",
        )
        block = format_agent_file_index_block(conversation)
        assert "Archivos subidos por el usuario" in block
        assert "Archivos generados por el agente" in block
        assert "solo lectura" in block

    def test_open_file_stream_serves_original_upload_bytes(self, user, conversation):
        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        file_bytes = build_sample_xlsx_bytes()
        file_obj = save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=file_bytes,
            parsed=parsed,
        )
        stream = open_file_stream(file_obj)
        assert stream.getvalue() == file_bytes

    def test_format_user_attachments_block(self, user, conversation):
        from apps.agent.events import persist_event
        from apps.chat.models import AgentEvent, Message

        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        file_obj = save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=build_sample_xlsx_bytes(),
            parsed=parsed,
        )
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Analiza este archivo",
        )
        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.FILE_CREATED,
            payload=serialize_file_for_ui(file_obj, user=user),
            message=user_message,
        )
        block = format_user_attachments_block(user_message)
        assert "Contexto adjunto en este mensaje" in block
        assert str(file_obj.id) in block
        assert "get_spreadsheet" in block

    def test_uploaded_file_index_shows_subido(self, user, conversation):
        parsed = parse_upload(build_sample_xlsx_bytes(), "ventas.xlsx")
        save_uploaded_file(
            conversation=conversation,
            user=user,
            original_name="ventas.xlsx",
            file_bytes=build_sample_xlsx_bytes(),
            parsed=parsed,
        )
        block = format_agent_file_index_block(conversation)
        assert "Archivos subidos por el usuario" in block
        assert "solo lectura" in block

    def test_serialize_file_for_ui(self, user, conversation):
        content = {
            "title": "Doc",
            "subtitle": "",
            "sections": [{"heading": "S", "paragraphs": [], "bullets": [], "table": None}],
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Doc.docx",
            content_json=content,
            file_bytes=b"x",
            preview_html="",
        )
        data = serialize_file_for_ui(file_obj)
        assert data["ext"] == "DOCX"
        assert data["kind"] == "doc"
        assert data["role"] == "deliverable"
        assert data["download_url"] == f"/files/{file_obj.id}/download/"

    def test_serialize_html_report_includes_pdf_url(self, user, conversation):
        from apps.files.models import HTML_MIME

        content = {
            "format": "html",
            "title": "Reporte",
            "subtitle": "",
            "html": "<main><p>Hola</p></main>",
            "body_html": "<main><p>Hola</p></main>",
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        data = serialize_file_for_ui(file_obj)
        assert data["ext"] == "HTML"
        assert data["format"] == "html"
        assert data["kind"] == "doc"
        assert data["meta"] == "Report · HTML"
        assert data["open_expanded"] is False
        assert data["download_pdf_url"] == f"/files/{file_obj.id}/download/pdf/"

    def test_serialize_dashboard_html_includes_open_expanded(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "",
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
        data = serialize_file_for_ui(file_obj)
        assert data["kind"] == "dashboard"
        assert data["name"] == "Ventas"
        assert data["meta"] == "Dashboard"
        assert data["open_expanded"] is True

    def test_normalize_legacy_dashboard_payload(self):
        payload = {
            "file_id": "abc",
            "name": "Ventas.html",
            "ext": "HTML",
            "meta": "Dashboard · HTML",
            "kind": "dashboard",
        }
        normalized = normalize_file_payload_for_ui(payload)
        assert normalized["name"] == "Ventas"
        assert normalized["meta"] == "Dashboard"
        assert normalized["kind"] == "dashboard"

    def test_normalize_html_filename_strips_malformed_trailing_json(self):
        corrupted = (
            "brecha-precio-vs-volumen-mexar.html'}] "
            "【analysis to=functions.publish_html_artifact malformed JSON"
        )
        assert _normalize_html_filename(corrupted, "fallback") == "brecha-precio-vs-volumen-mexar.html"

    def test_normalize_html_filename_preserves_spaces(self):
        assert _normalize_html_filename("mexar vs farmacias", "fallback") == "mexar vs farmacias.html"

    def test_serialize_file_for_ui_cleans_corrupted_dashboard_name(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Brecha de precio vs volumen vendido",
            "subtitle": "",
            "html": dashboard_html,
            "body_html": dashboard_html,
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="brecha-precio-vs-volumen-mexar.html'}] 【analysis to=functions.publish_html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        data = serialize_file_for_ui(file_obj)
        assert data["name"] == "brecha-precio-vs-volumen-mexar"

    def test_rename_dashboard_file_updates_name_and_title(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "",
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
        updated = rename_dashboard_file(file_obj, "ventas-hyalu")
        assert updated.original_name == "ventas-hyalu.html"
        assert updated.content_json["title"] == "ventas-hyalu"
        assert updated.version == 1

    def test_rename_dashboard_file_preserves_spaces(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "",
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
        updated = rename_dashboard_file(file_obj, "mexar vs farmacias")
        assert updated.original_name == "mexar vs farmacias.html"
        assert updated.content_json["title"] == "mexar vs farmacias"

    def test_rename_dashboard_file_sanitizes_invalid_chars(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "",
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
        updated = rename_dashboard_file(file_obj, 'bad<>:"/name')
        assert updated.original_name == "badname.html"
        assert updated.content_json["title"] == "badname"

    def test_rename_dashboard_file_rejects_non_dashboard(self, user, conversation):
        from apps.files.models import HTML_MIME

        content = {
            "format": "html",
            "title": "Reporte",
            "subtitle": "",
            "html": "<main><p>Hola</p></main>",
            "body_html": "<main><p>Hola</p></main>",
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        with pytest.raises(ValueError, match="Only dashboards"):
            rename_dashboard_file(file_obj, "nuevo-nombre")

    def test_hydrate_file_payload_for_ui_uses_current_db_name(self, user, conversation):
        from apps.files.models import HTML_MIME

        dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
        content = {
            "format": "html",
            "html_kind": "dashboard",
            "title": "Ventas",
            "subtitle": "",
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
        rename_dashboard_file(file_obj, "ventas-renombradas")
        stale_payload = {
            "file_id": str(file_obj.id),
            "name": "Ventas",
            "ext": "HTML",
            "meta": "Dashboard",
            "kind": "dashboard",
            "version": 1,
        }
        hydrated = hydrate_file_payload_for_ui(
            stale_payload,
            conversation_id=conversation.id,
        )
        assert hydrated["name"] == "ventas-renombradas"


def _dashboard_file(user, conversation):
    from apps.files.models import HTML_MIME

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
    return save_generated_file(
        conversation=conversation,
        user=user,
        original_name="Ventas.html",
        content_json=content,
        file_bytes=b"<html></html>",
        preview_html="<div></div>",
        mime_type=HTML_MIME,
    )


@pytest.mark.django_db
class TestSavedDashboardServices:
    def test_save_dashboard_creates_bookmark(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        saved = save_dashboard(user, file_obj)
        assert saved.user == user
        assert saved.file == file_obj
        assert is_dashboard_saved(user, file_obj.id)

    def test_save_dashboard_idempotent(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        first = save_dashboard(user, file_obj)
        second = save_dashboard(user, file_obj)
        assert first.id == second.id

    def test_save_dashboard_rejects_report(self, user, conversation):
        from apps.files.models import HTML_MIME

        content = {
            "format": "html",
            "title": "Reporte",
            "subtitle": "",
            "html": "<main><p>Hola</p></main>",
            "body_html": "<main><p>Hola</p></main>",
            "full_document": False,
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=b"<html></html>",
            preview_html="<div></div>",
            mime_type=HTML_MIME,
        )
        with pytest.raises(ValueError, match="Only dashboards"):
            save_dashboard(user, file_obj)

    def test_unsave_dashboard_removes_bookmark_not_file(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        save_dashboard(user, file_obj)
        assert unsave_dashboard(user, file_obj.id) is True
        assert not is_dashboard_saved(user, file_obj.id)
        assert File.objects.filter(id=file_obj.id).exists()

    def test_set_dashboard_pinned(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        save_dashboard(user, file_obj)
        saved = set_dashboard_pinned(user, file_obj.id, True)
        assert saved.pinned is True

    def test_list_saved_dashboards_filters_query(self, user, conversation):
        file_a = _dashboard_file(user, conversation)
        file_b = _dashboard_file(user, conversation)
        file_b.original_name = "Clientes.html"
        file_b.content_json["title"] = "Clientes"
        file_b.save(update_fields=["original_name", "content_json"])
        save_dashboard(user, file_a)
        save_dashboard(user, file_b)
        results = list(list_saved_dashboards(user, query="clientes"))
        assert len(results) == 1
        assert results[0].file_id == file_b.id

    def test_serialize_file_for_ui_includes_saved_flag(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        assert serialize_file_for_ui(file_obj, user=user)["saved"] is False
        save_dashboard(user, file_obj)
        assert serialize_file_for_ui(file_obj, user=user)["saved"] is True

    def test_serialize_saved_dashboard(self, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        saved = save_dashboard(user, file_obj)
        data = serialize_saved_dashboard(saved)
        assert data["name"] == "Ventas"
        assert data["saved"] is True
        assert data["author"]
        assert len(data["series"]) == 10
        assert data["sparkline_line"].startswith("M")
        assert data["sparkline_area"].endswith("Z")
