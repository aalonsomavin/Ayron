import json

import pytest
from django.contrib.auth import get_user_model

from apps.agent.context import set_agent_context
from apps.agent.tools.document import (
    build_docx,
    build_preview_html,
    create_document,
    get_document,
    list_conversation_files,
    update_document,
    validate_content_json,
)
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


@pytest.fixture
def user(db):
    return User.objects.create_user(username="docuser", password="pass")


@pytest.fixture
def conversation(user):
    return Conversation.objects.create(user=user)


@pytest.fixture
def sample_content():
    return {
        "title": "Informe de ventas",
        "subtitle": "Mayo 2026",
        "sections": [
            {
                "heading": "Resumen",
                "paragraphs": ["Las ventas subieron."],
                "bullets": ["Punto A"],
                "table": {"headers": ["Región", "Total"], "rows": [["EMEA", "$100k"]]},
            }
        ],
    }


@pytest.mark.django_db
class TestDocumentTool:
    def test_validate_content_json(self, sample_content):
        result = validate_content_json(
            sample_content["title"],
            sample_content["subtitle"],
            sample_content["sections"],
        )
        assert result["title"] == "Informe de ventas"
        assert len(result["sections"]) == 1

    def test_build_docx_returns_bytes(self, sample_content):
        content = validate_content_json(
            sample_content["title"],
            sample_content["subtitle"],
            sample_content["sections"],
        )
        docx_bytes = build_docx(content)
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 100
        assert docx_bytes[:2] == b"PK"

    def test_build_preview_html(self, sample_content):
        content = validate_content_json(
            sample_content["title"],
            sample_content["subtitle"],
            sample_content["sections"],
        )
        html = build_preview_html(content)
        assert "Informe de ventas" in html
        assert "ay-doc-preview__page" in html

    def test_create_document(self, user, conversation, sample_content):
        set_agent_context(conversation, user)
        result = json.loads(
            invoke_tool(
                create_document,
                "call_doc_1",
                title=sample_content["title"],
                subtitle=sample_content["subtitle"],
                sections=sample_content["sections"],
            )
        )
        assert result["ok"] is True
        assert result["action"] == "created"
        assert File.objects.count() == 1

    def test_list_and_get_document(self, user, conversation, sample_content):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_document,
                "call_doc_2",
                title=sample_content["title"],
                subtitle="",
                sections=sample_content["sections"],
            )
        )
        listed = json.loads(list_conversation_files.invoke({}))
        assert listed["ok"] is True
        assert len(listed["files"]) == 1

        fetched = json.loads(get_document.invoke({"file_id": created["file_id"]}))
        assert fetched["ok"] is True
        assert fetched["content_json"]["title"] == sample_content["title"]

    def test_update_document(self, user, conversation, sample_content):
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_document,
                "call_doc_3",
                title=sample_content["title"],
                subtitle="",
                sections=sample_content["sections"],
            )
        )
        updated = json.loads(
            invoke_tool(
                update_document,
                "call_doc_4",
                file_id=created["file_id"],
                title="Informe actualizado",
            )
        )
        assert updated["ok"] is True
        assert updated["version"] == 2
        file_obj = File.objects.get(id=created["file_id"])
        assert file_obj.content_json["title"] == "Informe actualizado"

    def test_update_document_wrong_conversation(self, user, conversation, sample_content):
        other = Conversation.objects.create(user=user)
        set_agent_context(conversation, user)
        created = json.loads(
            invoke_tool(
                create_document,
                "call_doc_5",
                title=sample_content["title"],
                subtitle="",
                sections=sample_content["sections"],
            )
        )
        set_agent_context(other, user)
        result = json.loads(
            invoke_tool(
                update_document,
                "call_doc_6",
                file_id=created["file_id"],
                title="Hack",
            )
        )
        assert result["ok"] is False
