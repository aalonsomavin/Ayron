import json
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from apps.agent.tools.errors import AGENT_INSTRUCTION_ON_TOOL_ERROR, build_tool_error_response


def _tool_name(request: ToolCallRequest) -> str:
    if request.tool:
        return request.tool.name
    return request.tool_call["name"]


def _tool_call_id(request: ToolCallRequest) -> str | None:
    return request.tool_call.get("id")


def _extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


def _try_parse_json(text: str) -> dict | None:
    if not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _enrich_tool_message(result: ToolMessage, tool_name: str, tool_call_id: str | None) -> ToolMessage:
    text = _extract_text_content(result.content)
    parsed = _try_parse_json(text)
    if parsed is None or parsed.get("ok") is not False or "agent_instruction" in parsed:
        return result

    enriched = {**parsed, "agent_instruction": AGENT_INSTRUCTION_ON_TOOL_ERROR}
    return ToolMessage(
        content=json.dumps(enriched),
        tool_call_id=tool_call_id or result.tool_call_id,
        name=tool_name or result.name,
        status="error",
    )


class ToolFailureFeedbackMiddleware(AgentMiddleware):
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tool_name = _tool_name(request)
        tool_call_id = _tool_call_id(request)
        try:
            result = handler(request)
        except Exception as exc:
            return ToolMessage(
                content=build_tool_error_response(str(exc)),
                tool_call_id=tool_call_id,
                name=tool_name,
                status="error",
            )
        if isinstance(result, Command):
            return result
        if isinstance(result, ToolMessage):
            return _enrich_tool_message(result, tool_name, tool_call_id)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = _tool_name(request)
        tool_call_id = _tool_call_id(request)
        try:
            result = await handler(request)
        except Exception as exc:
            return ToolMessage(
                content=build_tool_error_response(str(exc)),
                tool_call_id=tool_call_id,
                name=tool_name,
                status="error",
            )
        if isinstance(result, Command):
            return result
        if isinstance(result, ToolMessage):
            return _enrich_tool_message(result, tool_name, tool_call_id)
        return result
