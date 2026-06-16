import pytest
from django.contrib.auth import get_user_model

from apps.agent.runner import build_system_prompt
from apps.chat.models import Conversation
from apps.files.services import save_generated_file

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="promptuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.mark.django_db
class TestAgentFileAwareness:
    def test_system_prompt_includes_file_index(self, user, conversation):
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
        prompt = build_system_prompt(conversation)
        assert "Archivos de esta conversación" in prompt
        assert "file_id=" in prompt

    def test_system_prompt_without_files(self, conversation):
        prompt = build_system_prompt(conversation)
        assert "Archivos de esta conversación" not in prompt
