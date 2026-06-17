import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import ToolMessage

from apps.agent.middleware.tool_errors import ToolFailureFeedbackMiddleware
from apps.agent.tools.errors import (
    AGENT_INSTRUCTION_ON_QUERY_ERROR,
    AGENT_INSTRUCTION_ON_TOOL_ERROR,
    build_query_error_response,
    build_tool_error_response,
)


class TestBuildToolErrorResponse:
    def test_includes_ok_false_and_instruction(self):
        result = json.loads(build_tool_error_response("boom"))
        assert result["ok"] is False
        assert result["error"] == "boom"
        assert result["agent_instruction"] == AGENT_INSTRUCTION_ON_TOOL_ERROR

    def test_includes_extra_fields(self):
        result = json.loads(build_tool_error_response("boom", hint="try again"))
        assert result["hint"] == "try again"

    def test_query_error_uses_silent_retry_instruction(self):
        result = json.loads(build_query_error_response("syntax error"))
        assert result["agent_instruction"] == AGENT_INSTRUCTION_ON_QUERY_ERROR
        assert "No menciones al usuario" in result["agent_instruction"]


def _make_request(tool_name="my_tool", tool_call_id="call_1"):
    request = MagicMock()
    request.tool = None
    request.tool_call = {"name": tool_name, "id": tool_call_id}
    return request


class TestToolFailureFeedbackMiddleware:
    def test_catches_exception_and_returns_tool_message(self):
        middleware = ToolFailureFeedbackMiddleware()
        request = _make_request()

        def handler(_request):
            raise RuntimeError("failed")

        result = middleware.wrap_tool_call(request, handler)
        assert isinstance(result, ToolMessage)
        payload = json.loads(result.content)
        assert payload["ok"] is False
        assert "failed" in payload["error"]
        assert payload["agent_instruction"] == AGENT_INSTRUCTION_ON_TOOL_ERROR
        assert result.status == "error"
        assert result.tool_call_id == "call_1"
        assert result.name == "my_tool"

    def test_enriches_ok_false_without_instruction(self):
        middleware = ToolFailureFeedbackMiddleware()
        request = _make_request()

        def handler(_request):
            return ToolMessage(
                content='{"ok": false, "error": "bad input"}',
                tool_call_id="call_1",
                name="my_tool",
            )

        result = middleware.wrap_tool_call(request, handler)
        payload = json.loads(result.content)
        assert payload["agent_instruction"] == AGENT_INSTRUCTION_ON_TOOL_ERROR
        assert result.status == "error"

    def test_leaves_success_response_unchanged(self):
        middleware = ToolFailureFeedbackMiddleware()
        request = _make_request()

        def handler(_request):
            return ToolMessage(
                content='{"ok": true, "value": 1}',
                tool_call_id="call_1",
                name="my_tool",
            )

        result = middleware.wrap_tool_call(request, handler)
        assert json.loads(result.content) == {"ok": True, "value": 1}
        assert result.status == "success"

    def test_async_catches_exception(self):
        import asyncio

        middleware = ToolFailureFeedbackMiddleware()
        request = _make_request()

        async def handler(_request):
            raise RuntimeError("async failed")

        result = asyncio.run(middleware.awrap_tool_call(request, handler))
        payload = json.loads(result.content)
        assert payload["ok"] is False
        assert "async failed" in payload["error"]
