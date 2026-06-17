import json
from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from apps.agent.context import (
    get_deliverable_intent,
    get_deliverable_nudge_count,
    increment_deliverable_nudge_count,
)
from apps.agent.deliverable_intent import (
    DeliverableIntent,
    format_deliverable_nudge,
    required_tools_for_intent,
)

MAX_DELIVERABLE_NUDGES = 2


def _messages_since_last_user(messages: Sequence) -> list:
    last_user_idx = -1
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            last_user_idx = index
    if last_user_idx < 0:
        return list(messages)
    return list(messages[last_user_idx + 1 :])


def _extract_tool_message_content(content) -> dict | None:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "".join(parts)
    else:
        return None
    if not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def deliverable_satisfied(messages: Sequence, intent: DeliverableIntent) -> bool:
    required = required_tools_for_intent(intent)
    if not required:
        return True
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        tool_name = message.name or ""
        if tool_name not in required:
            continue
        parsed = _extract_tool_message_content(message.content)
        if parsed and parsed.get("ok") is True:
            return True
    return False


class DeliverableGuardMiddleware(AgentMiddleware):
    @hook_config(can_jump_to=["model"])
    def after_model(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        intent = get_deliverable_intent()
        if intent is None or intent == DeliverableIntent.NONE:
            return None

        messages = state.get("messages", [])
        if not messages:
            return None

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return None
        if last_message.tool_calls:
            return None

        turn_messages = _messages_since_last_user(messages)
        if deliverable_satisfied(turn_messages, intent):
            return None

        if get_deliverable_nudge_count() >= MAX_DELIVERABLE_NUDGES:
            return None

        increment_deliverable_nudge_count()
        nudge = format_deliverable_nudge(intent)
        if not nudge:
            return None

        return {
            "messages": [HumanMessage(content=nudge)],
            "jump_to": "model",
        }
