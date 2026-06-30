import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.chat.models import Conversation
from apps.files.services import save_generated_file

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="fileviewuser", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otherfileuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.fixture
def file_obj(user, conversation):
    content = {
        "title": "Doc",
        "subtitle": "",
        "sections": [{"heading": "S", "paragraphs": ["p"], "bullets": [], "table": None}],
    }
    return save_generated_file(
        conversation=conversation,
        user=user,
        original_name="Doc.docx",
        content_json=content,
        file_bytes=b"docx-bytes",
        preview_html="<div class='ay-doc-preview'><div class='ay-doc-preview__source'>preview</div><div class='ay-doc-preview__pages'></div></div>",
    )


@pytest.mark.django_db
class TestFileViews:
    def test_download_owner(self, client, user, file_obj):
        client.force_login(user)
        url = reverse("files:download", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment")

    def test_download_other_user_forbidden(self, client, other_user, file_obj):
        client.force_login(other_user)
        url = reverse("files:download", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 404

    def test_preview_owner(self, client, user, file_obj):
        client.force_login(user)
        url = reverse("files:preview", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert b"ay-doc-preview" in response.content
        assert b"ay-doc-preview__doc-header" in response.content

    def test_preview_regenerates_from_content_json(self, client, user, conversation):
        stale_brand = (
            '<div class="ay-doc-preview" data-page-width-px="816" data-page-height-px="1056" '
            'data-page-margin-px="96">'
            '<div class="ay-doc-preview__source">'
            '<div class="ay-doc-preview__brand"><div class="ay-doc-preview__brand-name">AyronOne</div>'
            '<div class="ay-doc-preview__brand-caption">Generado con AyronOne</div></div>'
            '<h1 class="ay-doc-preview__title">Viejo</h1></div>'
            '<div class="ay-doc-preview__pages"></div></div>'
        )
        content = {
            "title": "Informe actualizado",
            "subtitle": "Junio 2026",
            "sections": [
                {
                    "heading": "Resumen",
                    "blocks": [{"type": "paragraph", "text": "Contenido nuevo."}],
                }
            ],
        }
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Informe.docx",
            content_json=content,
            file_bytes=b"docx-bytes",
            preview_html=stale_brand,
        )
        client.force_login(user)
        url = reverse("files:preview", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Informe actualizado" in response.content
        assert b"ay-doc-preview__doc-header" in response.content
        assert b"AyronOne" not in response.content
        assert b"Generado con AyronOne" not in response.content

    def test_xlsx_preview_owner(self, client, user, conversation):
        from apps.agent.tools.spreadsheet import build_preview_html, build_xlsx, validate_content_json
        from apps.files.models import XLSX_MIME

        content = validate_content_json(
            "Desglose regional",
            [
                {
                    "name": "Revenue",
                    "headers": ["Region", "Revenue"],
                    "rows": [["EMEA", "486,200"]],
                }
            ],
        )
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="regional.xlsx",
            content_json=content,
            file_bytes=build_xlsx(content),
            preview_html=build_preview_html(content),
            mime_type=XLSX_MIME,
        )
        client.force_login(user)
        url = reverse("files:preview", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"ay-sheet-preview" in response.content
        assert b"EMEA" in response.content

    def test_html_preview_owner(self, client, user, conversation):
        from apps.agent.tools.html_report import (
            build_export_html,
            build_preview_fragment,
            validate_html_report_content,
        )
        from apps.files.models import HTML_MIME
        from apps.files.services import save_generated_file

        content = validate_html_report_content(
            "Reporte HTML",
            "<main><h1>Contenido del reporte.</h1><table><tr><td>A</td></tr></table></main>",
            "Junio 2026",
        )
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=build_export_html(content).encode("utf-8"),
            preview_html=build_preview_fragment(content),
            mime_type=HTML_MIME,
        )
        client.force_login(user)
        url = reverse("files:preview", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.content
        assert b"ay-html-report-preview" in response.content
        assert b"<table>" in response.content

    def test_html_download_owner(self, client, user, conversation):
        from apps.agent.tools.html_report import (
            build_export_html,
            build_preview_fragment,
            validate_html_report_content,
        )
        from apps.files.models import HTML_MIME
        from apps.files.services import save_generated_file

        content = validate_html_report_content("Reporte", "<p>Hola</p>", "")
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=build_export_html(content).encode("utf-8"),
            preview_html=build_preview_fragment(content),
            mime_type=HTML_MIME,
        )
        client.force_login(user)
        url = reverse("files:download", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        body = b"".join(response.streaming_content)
        assert b"<!DOCTYPE html>" in body

    def test_download_pdf_html_report(self, client, user, conversation, monkeypatch):
        from apps.agent.tools.html_report import (
            build_export_html,
            build_preview_fragment,
            validate_html_report_content,
        )
        from apps.files.models import HTML_MIME
        from apps.files.services import save_generated_file

        content = validate_html_report_content("Reporte PDF", "<p>Hola</p>", "")
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=build_export_html(content).encode("utf-8"),
            preview_html=build_preview_fragment(content),
            mime_type=HTML_MIME,
        )

        monkeypatch.setattr(
            "apps.files.views.html_to_pdf",
            lambda html: b"%PDF-mock" + html[:20].encode("utf-8"),
        )

        client.force_login(user)
        url = reverse("files:download_pdf", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-mock")

    def test_download_pdf_docx_not_found(self, client, user, file_obj):
        client.force_login(user)
        url = reverse("files:download_pdf", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 404


def _dashboard_file(user, conversation):
    from apps.files.models import HTML_MIME
    from apps.files.services import save_generated_file

    dashboard_html = '<div class="ay-dash-page"><div class="ay-dash-inner"></div></div>'
    content = {
        "format": "html",
        "html_kind": "dashboard",
        "title": "dashboard-ventas",
        "subtitle": "",
        "html": dashboard_html,
        "body_html": dashboard_html,
        "full_document": False,
    }
    return save_generated_file(
        conversation=conversation,
        user=user,
        original_name="dashboard-ventas.html",
        content_json=content,
        file_bytes=b"<html></html>",
        preview_html="<div></div>",
        mime_type=HTML_MIME,
    )


@pytest.mark.django_db
class TestFileRename:
    def test_rename_dashboard_owner(self, client, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        client.force_login(user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "dashboard-hyalufresh"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "dashboard-hyalufresh"
        file_obj.refresh_from_db()
        assert file_obj.original_name == "dashboard-hyalufresh.html"
        assert file_obj.content_json["title"] == "dashboard-hyalufresh"

    def test_rename_dashboard_with_spaces(self, client, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        client.force_login(user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "mexar vs farmacias"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "mexar vs farmacias"
        file_obj.refresh_from_db()
        assert file_obj.original_name == "mexar vs farmacias.html"
        assert file_obj.content_json["title"] == "mexar vs farmacias"

    def test_rename_dashboard_empty_name(self, client, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        client.force_login(user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_rename_dashboard_other_user(self, client, other_user, user, conversation):
        file_obj = _dashboard_file(user, conversation)
        client.force_login(other_user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "otro-nombre"}),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_rename_html_report_not_found(self, client, user, conversation):
        from apps.agent.tools.html_report import (
            build_export_html,
            build_preview_fragment,
            validate_html_report_content,
        )
        from apps.files.models import HTML_MIME
        from apps.files.services import save_generated_file

        content = validate_html_report_content("Reporte", "<p>Hola</p>", "")
        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Reporte.html",
            content_json=content,
            file_bytes=build_export_html(content).encode("utf-8"),
            preview_html=build_preview_fragment(content),
            mime_type=HTML_MIME,
        )
        client.force_login(user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "nuevo"}),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_rename_docx_not_found(self, client, user, file_obj):
        client.force_login(user)
        url = reverse("files:rename", kwargs={"file_id": file_obj.id})
        response = client.post(
            url,
            data=json.dumps({"name": "nuevo"}),
            content_type="application/json",
        )
        assert response.status_code == 404
