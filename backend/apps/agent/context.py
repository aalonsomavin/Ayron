from contextvars import ContextVar
from typing import TYPE_CHECKING

from apps.agent.deliverable_intent import DeliverableIntent
from apps.chat.models import Conversation, Message

if TYPE_CHECKING:
    from deepagents.backends.protocol import BackendProtocol

_conversation_ctx: ContextVar[Conversation | None] = ContextVar("agent_conversation", default=None)
_user_ctx: ContextVar = ContextVar("agent_user", default=None)
_message_ctx: ContextVar[Message | None] = ContextVar("agent_message", default=None)
_deliverable_intent_ctx: ContextVar[DeliverableIntent | None] = ContextVar(
    "agent_deliverable_intent",
    default=None,
)
_deliverable_nudge_count_ctx: ContextVar[int] = ContextVar("agent_deliverable_nudge_count", default=0)
_backend_ctx: ContextVar["BackendProtocol | None"] = ContextVar("agent_backend", default=None)
_sql_tool_trace_inputs: dict[str, dict[str, str]] = {}


def clear_sql_tool_trace_inputs() -> None:
    _sql_tool_trace_inputs.clear()


def record_sql_tool_trace_input(tool_call_id: str, *, sql: str, purpose: str) -> None:
    if not tool_call_id:
        return
    _sql_tool_trace_inputs[tool_call_id] = {
        "sql": sql.strip(),
        "purpose": purpose.strip(),
    }


def pop_sql_tool_trace_input(tool_call_id: str) -> dict[str, str] | None:
    if not tool_call_id:
        return None
    return _sql_tool_trace_inputs.pop(tool_call_id, None)


def peek_sql_tool_trace_input(tool_call_id: str) -> dict[str, str] | None:
    if not tool_call_id:
        return None
    traced = _sql_tool_trace_inputs.get(tool_call_id)
    if not traced:
        return None
    return dict(traced)


def reset_agent_context() -> None:
    _conversation_ctx.set(None)
    _user_ctx.set(None)
    _message_ctx.set(None)
    _deliverable_intent_ctx.set(None)
    _deliverable_nudge_count_ctx.set(0)


def set_agent_context(
    conversation: Conversation,
    user,
    *,
    deliverable_intent: DeliverableIntent | None = None,
    message: Message | None = None,
) -> None:
    _conversation_ctx.set(conversation)
    _user_ctx.set(user)
    _message_ctx.set(message)
    _deliverable_intent_ctx.set(deliverable_intent)
    _deliverable_nudge_count_ctx.set(0)


def get_agent_conversation() -> Conversation | None:
    return _conversation_ctx.get()


def get_agent_user():
    return _user_ctx.get()


def get_agent_message() -> Message | None:
    return _message_ctx.get()


def get_deliverable_intent() -> DeliverableIntent | None:
    return _deliverable_intent_ctx.get()


def set_deliverable_intent(intent: DeliverableIntent | None) -> None:
    _deliverable_intent_ctx.set(intent)
    _deliverable_nudge_count_ctx.set(0)


def get_deliverable_nudge_count() -> int:
    return _deliverable_nudge_count_ctx.get()


def increment_deliverable_nudge_count() -> int:
    count = _deliverable_nudge_count_ctx.get() + 1
    _deliverable_nudge_count_ctx.set(count)
    return count


def reset_deliverable_guard_state() -> None:
    _deliverable_intent_ctx.set(None)
    _deliverable_nudge_count_ctx.set(0)


def set_agent_backend(backend: "BackendProtocol") -> None:
    _backend_ctx.set(backend)


def get_agent_backend() -> "BackendProtocol":
    backend = _backend_ctx.get()
    if backend is None:
        raise RuntimeError("Agent backend is not set for the current context")
    return backend
