import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from apps.agent.context import (
    reset_deliverable_guard_state,
    set_deliverable_intent,
)
from apps.agent.deliverable_intent import DeliverableIntent
from apps.agent.middleware.deliverable_guard import (
    DeliverableGuardMiddleware,
    deliverable_satisfied,
)


@pytest.fixture(autouse=True)
def _reset_guard_state():
    reset_deliverable_guard_state()
    yield
    reset_deliverable_guard_state()


class TestDeliverableSatisfied:
    def test_not_satisfied_with_draft_create_only(self):
        messages = [
            ToolMessage(
                content=json.dumps({"ok": True, "file_id": "abc", "draft": True}),
                tool_call_id="call_1",
                name="create_html_report",
            )
        ]
        assert deliverable_satisfied(messages, DeliverableIntent.CREATE_HTML) is False

    def test_satisfied_after_publish_html_report(self):
        messages = [
            ToolMessage(
                content=json.dumps({"ok": True, "file_id": "abc", "draft": True}),
                tool_call_id="call_1",
                name="create_html_report",
            ),
            ToolMessage(
                content=json.dumps({"ok": True, "file_id": "abc"}),
                tool_call_id="call_2",
                name="publish_html_report",
            ),
        ]
        assert deliverable_satisfied(messages, DeliverableIntent.CREATE_HTML) is True

    def test_satisfied_after_successful_create_html_report(self):
        messages = [
            ToolMessage(
                content=json.dumps({"ok": True, "file_id": "abc"}),
                tool_call_id="call_1",
                name="create_html_report",
            )
        ]
        assert deliverable_satisfied(messages, DeliverableIntent.CREATE_HTML) is True

    def test_not_satisfied_without_tool(self):
        messages = [AIMessage(content="Aquí está el informe en texto.")]
        assert deliverable_satisfied(messages, DeliverableIntent.CREATE_HTML) is False

    def test_update_satisfied_with_either_update_tool(self):
        messages = [
            ToolMessage(
                content=json.dumps({"ok": True, "file_id": "abc"}),
                tool_call_id="call_1",
                name="update_document",
            )
        ]
        assert deliverable_satisfied(messages, DeliverableIntent.UPDATE_FILE) is True


class TestDeliverableGuardMiddleware:
    def test_nudges_when_deliverable_missing(self):
        set_deliverable_intent(DeliverableIntent.CREATE_HTML)
        middleware = DeliverableGuardMiddleware()
        state = {
            "messages": [
                HumanMessage(content="Preparame un informe de ventas"),
                AIMessage(content="Estas son las ventas del mes."),
            ]
        }

        result = middleware.after_model(state, MagicMock())

        assert result is not None
        assert result["jump_to"] == "model"
        assert "create_html_report" in result["messages"][0].content

    def test_no_nudge_when_deliverable_created(self):
        set_deliverable_intent(DeliverableIntent.CREATE_HTML)
        middleware = DeliverableGuardMiddleware()
        state = {
            "messages": [
                HumanMessage(content="Preparame un informe de ventas"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_1", "name": "create_html_report", "args": {}},
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"ok": True, "file_id": "abc"}),
                    tool_call_id="call_1",
                    name="create_html_report",
                ),
                AIMessage(content="Listo."),
            ]
        }

        result = middleware.after_model(state, MagicMock())

        assert result is None

    def test_no_nudge_when_intent_none(self):
        set_deliverable_intent(DeliverableIntent.NONE)
        middleware = DeliverableGuardMiddleware()
        state = {
            "messages": [
                HumanMessage(content="¿Top 5 artistas?"),
                AIMessage(content="Los cinco principales son..."),
            ]
        }

        result = middleware.after_model(state, MagicMock())

        assert result is None

    def test_stops_after_max_nudges(self):
        set_deliverable_intent(DeliverableIntent.CREATE_HTML)
        middleware = DeliverableGuardMiddleware()
        state = {
            "messages": [
                HumanMessage(content="Preparame un informe"),
                AIMessage(content="Solo texto."),
            ]
        }

        first = middleware.after_model(state, MagicMock())
        second = middleware.after_model(state, MagicMock())
        third = middleware.after_model(state, MagicMock())

        assert first is not None
        assert second is not None
        assert third is None

    def test_no_nudge_when_model_still_calling_tools(self):
        set_deliverable_intent(DeliverableIntent.CREATE_HTML)
        middleware = DeliverableGuardMiddleware()
        state = {
            "messages": [
                HumanMessage(content="Preparame un informe"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "run_sql_query", "args": {}}],
                ),
            ]
        }

        result = middleware.after_model(state, MagicMock())

        assert result is None
