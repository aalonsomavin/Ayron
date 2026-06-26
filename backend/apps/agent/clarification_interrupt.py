from typing import Any

from langchain.agents.middleware.human_in_the_loop import HITLRequest
from langchain_core.messages import AIMessage

CLARIFICATION_TOOL = "ask_clarification"


def _iter_interrupt_values(state: Any) -> list[Any]:
    interrupts = getattr(state, "interrupts", ()) or ()
    values = []
    for item in interrupts:
        value = item.value if hasattr(item, "value") else item.get("value")
        values.append(value)
    return values


def has_clarification_interrupt(state: Any) -> bool:
    for value in _iter_interrupt_values(state):
        if isinstance(value, dict):
            for action in value.get("action_requests", []):
                if action.get("name") == CLARIFICATION_TOOL:
                    return True
        elif isinstance(value, HITLRequest):
            for action in value.get("action_requests", []):
                if action.get("name") == CLARIFICATION_TOOL:
                    return True
    return False


def find_clarification_tool_call(messages: list) -> tuple[str, dict] | None:
    for message in reversed(messages or []):
        if not isinstance(message, AIMessage):
            continue
        for tool_call in message.tool_calls or []:
            if tool_call.get("name") == CLARIFICATION_TOOL:
                tool_call_id = tool_call.get("id")
                args = tool_call.get("args") or {}
                if tool_call_id:
                    return tool_call_id, args if isinstance(args, dict) else {}
    return None
