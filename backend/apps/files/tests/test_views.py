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
        docx_bytes=b"docx-bytes",
        preview_html="<div class='ay-doc-preview__page'>preview</div>",
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
        assert b"ay-doc-preview__page" in response.content
