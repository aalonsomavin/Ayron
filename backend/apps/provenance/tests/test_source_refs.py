import pytest
from django.contrib.auth import get_user_model

from apps.provenance.models import DataAccess
from apps.provenance.source_refs import (
    SOURCE_REF_KIND_CHAT_SHEET,
    SOURCE_REF_KIND_INTEGRATION_SHEET,
    SOURCE_REF_KIND_SQL,
    allocate_source_ref,
    format_available_source_refs,
    resolve_source_identifiers,
)
from apps.chat.models import Conversation

User = get_user_model()


@pytest.fixture
def conversation(db):
    user = User.objects.create_user(username="refuser", password="pass")
    return Conversation.objects.create(user=user, title="Refs")


@pytest.mark.django_db
class TestSourceRefs:
    def test_allocate_independent_counters(self, conversation):
        DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="sql-1",
            access_kind=DataAccess.AccessKind.SQL,
            source_ref="sql_1",
            request={},
            response_summary={},
        )
        DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="chat-1",
            access_kind=DataAccess.AccessKind.SPREADSHEET,
            source_ref="chat_sheet_1",
            request={},
            response_summary={"source_origin": "chat_upload"},
        )
        DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="int-1",
            access_kind=DataAccess.AccessKind.SPREADSHEET,
            source_ref="integration_sheet_1",
            request={},
            response_summary={"source_origin": "integration"},
        )

        assert allocate_source_ref(conversation, SOURCE_REF_KIND_SQL) == "sql_2"
        assert allocate_source_ref(conversation, SOURCE_REF_KIND_CHAT_SHEET) == "chat_sheet_2"
        assert allocate_source_ref(conversation, SOURCE_REF_KIND_INTEGRATION_SHEET) == "integration_sheet_2"

    def test_resolve_mixed_refs(self, conversation):
        sql_access = DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="sql-a",
            access_kind=DataAccess.AccessKind.SQL,
            source_ref="sql_1",
            request={},
            response_summary={},
        )
        sheet_access = DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="sheet-a",
            access_kind=DataAccess.AccessKind.SPREADSHEET,
            source_ref="chat_sheet_1",
            request={},
            response_summary={"source_origin": "chat_upload"},
        )
        found = resolve_source_identifiers(conversation, ["sql_1", "chat_sheet_1"])
        assert found["sql_1"] == sql_access
        assert found["chat_sheet_1"] == sheet_access

    def test_format_available_source_refs_lists_all(self, conversation):
        DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="sql-a",
            access_kind=DataAccess.AccessKind.SQL,
            source_ref="sql_1",
            request={"purpose": "Ventas"},
            response_summary={},
        )
        DataAccess.objects.create(
            conversation=conversation,
            tool_call_id="sheet-a",
            access_kind=DataAccess.AccessKind.SPREADSHEET,
            source_ref="chat_sheet_1",
            request={},
            response_summary={"user_summary": "Adjunto Q1"},
        )
        formatted = format_available_source_refs(conversation)
        assert "sql_1 (Ventas)" in formatted
        assert "chat_sheet_1 (Adjunto Q1)" in formatted
