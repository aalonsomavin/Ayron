import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.chat.models import Conversation
from apps.files.models import SavedDashboard
from apps.files.services import is_dashboard_saved, save_dashboard

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="saveduser", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="othersaved", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.fixture
def dashboard_file(user, conversation):
    from apps.files.models import HTML_MIME
    from apps.files.services import save_generated_file

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
class TestSavedDashboardViews:
    def test_saved_list_requires_auth(self, client):
        url = reverse("dashboards:saved_list")
        response = client.get(url)
        assert response.status_code == 302

    def test_saved_list_renders_items(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        response = client.get(reverse("dashboards:saved_list"))
        assert response.status_code == 200
        assert b"Anal\xc3\xadticas" in response.content
        assert b"Ventas" in response.content
        assert b"ay-saved-card__spark" in response.content

    def test_saved_list_search_htmx(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        response = client.get(
            reverse("dashboards:saved_list"),
            {"q": "ventas"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"Ventas" in response.content
        assert b"resultado" in response.content

    def test_saved_list_pin_htmx_refreshes_grid(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        response = client.post(
            reverse("files:pin", kwargs={"file_id": dashboard_file.id}),
            {"pinned": "true"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="dashboards-view",
        )
        assert response.status_code == 200
        assert b'id="dashboards-view"' in response.content
        assert b"Fijados" in response.content

    def test_saved_list_empty_state(self, client, user):
        client.force_login(user)
        response = client.get(reverse("dashboards:saved_list"))
        assert response.status_code == 200
        assert "Todavía no guardaste dashboards".encode() in response.content

    def test_saved_dashboard_detail_requires_auth(self, client, dashboard_file):
        url = reverse("dashboards:detail", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 302

    def test_saved_dashboard_detail_renders_full_view(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("dashboards:detail", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Ventas" in response.content
        assert b"hx-get" in response.content
        assert f'/dashboards/{dashboard_file.id}/preview/'.encode() in response.content

    def test_saved_dashboard_preview_returns_iframe(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("dashboards:preview", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"ay-dash-detail__iframe" in response.content
        assert b"srcdoc=" in response.content

    def test_saved_dashboard_detail_htmx_returns_partial(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("dashboards:detail", kwargs={"file_id": dashboard_file.id})
        response = client.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert b'id="dashboards-view"' in response.content
        assert b"<!DOCTYPE html>" not in response.content

    def test_saved_dashboard_detail_shows_pinned_state(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        pin_url = reverse("files:pin", kwargs={"file_id": dashboard_file.id})
        client.post(
            pin_url,
            data=json.dumps({"pinned": True}),
            content_type="application/json",
        )
        url = reverse("dashboards:detail", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"ay-dash-detail__btn--active" in response.content
        assert b'aria-pressed="true"' in response.content

    def test_saved_dashboard_detail_rejects_non_dashboard(self, client, user, conversation):
        from apps.files.services import save_generated_file

        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Doc.docx",
            content_json={
                "title": "Doc",
                "subtitle": "",
                "sections": [{"heading": "S", "paragraphs": ["p"], "bullets": [], "table": None}],
            },
            file_bytes=b"docx",
            preview_html="<div></div>",
        )
        client.force_login(user)
        url = reverse("dashboards:detail", kwargs={"file_id": file_obj.id})
        response = client.get(url)
        assert response.status_code == 404

    def test_file_save_creates_bookmark(self, client, user, dashboard_file):
        client.force_login(user)
        url = reverse("files:save", kwargs={"file_id": dashboard_file.id})
        response = client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data["saved"] is True
        assert SavedDashboard.objects.filter(user=user, file=dashboard_file).exists()

    def test_file_save_rejects_docx(self, client, user, conversation):
        from apps.files.services import save_generated_file

        file_obj = save_generated_file(
            conversation=conversation,
            user=user,
            original_name="Doc.docx",
            content_json={
                "title": "Doc",
                "subtitle": "",
                "sections": [{"heading": "S", "paragraphs": ["p"], "bullets": [], "table": None}],
            },
            file_bytes=b"docx",
            preview_html="<div></div>",
        )
        client.force_login(user)
        url = reverse("files:save", kwargs={"file_id": file_obj.id})
        response = client.post(url)
        assert response.status_code == 404

    def test_file_unsave_removes_bookmark(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("files:unsave", kwargs={"file_id": dashboard_file.id})
        response = client.post(url)
        assert response.status_code == 200
        assert response.json()["saved"] is False
        assert not is_dashboard_saved(user, dashboard_file.id)

    def test_file_pin_updates_bookmark(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("files:pin", kwargs={"file_id": dashboard_file.id})
        response = client.post(
            url,
            data=json.dumps({"pinned": True}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["pinned"] is True

    def test_file_save_other_user_forbidden(self, client, other_user, user, dashboard_file):
        client.force_login(other_user)
        url = reverse("files:save", kwargs={"file_id": dashboard_file.id})
        response = client.post(url)
        assert response.status_code == 404

    def test_file_save_button_renders_guardar(self, client, user, dashboard_file):
        client.force_login(user)
        url = reverse("files:save_button", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guardar" in response.content
        assert b"bookmark" in response.content or b"ay-artifact-panel__save" in response.content

    def test_file_save_button_renders_guardado_when_saved(self, client, user, dashboard_file):
        save_dashboard(user, dashboard_file)
        client.force_login(user)
        url = reverse("files:save_button", kwargs={"file_id": dashboard_file.id})
        response = client.get(url)
        assert response.status_code == 200
        assert b"Guardado" in response.content
        assert b"ay-artifact-panel__save--saved" in response.content

    def test_file_save_htmx_returns_artifact_button(self, client, user, dashboard_file):
        client.force_login(user)
        url = reverse("files:save", kwargs={"file_id": dashboard_file.id})
        response = client.post(url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="artifact-save")
        assert response.status_code == 200
        assert b"Guardado" in response.content
        assert b"ay-artifact-panel__save--saved" in response.content
