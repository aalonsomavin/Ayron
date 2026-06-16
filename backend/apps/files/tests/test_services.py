import pytest
from django.contrib.auth import get_user_model

from apps.chat.models import Conversation
from apps.files.models import File
from apps.files.services import (
    format_agent_file_index_block,
    get_agent_file_index,
    save_generated_file,
    serialize_file_for_ui,
    update_generated_file,
)

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
        assert "Archivos de esta conversación" in block
        assert "file_id=" in block

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
        assert data["meta"] == "Report · HTML"
        assert data["download_pdf_url"] == f"/files/{file_obj.id}/download/pdf/"
