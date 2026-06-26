import pytest
from django.contrib.auth import get_user_model

from apps.agent.events import persist_event
from apps.agent.runner import build_system_prompt
from apps.chat.models import AgentEvent, Conversation, Message
from apps.files.parsers import parse_upload
from apps.files.services import (
    save_generated_file,
    save_uploaded_file,
    serialize_file_for_ui,
)
from apps.files.tests.test_parsers_xlsx import build_sample_xlsx_bytes

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

    def test_system_prompt_includes_attachments_block(self, user, conversation):
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
            content="Analiza el Excel",
        )
        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.FILE_CREATED,
            payload=serialize_file_for_ui(file_obj, user=user),
            message=user_message,
        )
        prompt = build_system_prompt(conversation, user_message=user_message)
        assert "Archivos adjuntos en este mensaje" in prompt
        assert "get_spreadsheet" in prompt
