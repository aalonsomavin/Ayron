from contextvars import ContextVar

from apps.agent.deliverable_intent import DeliverableIntent
from apps.chat.models import Conversation

_conversation_ctx: ContextVar[Conversation | None] = ContextVar("agent_conversation", default=None)
_user_ctx: ContextVar = ContextVar("agent_user", default=None)
_deliverable_intent_ctx: ContextVar[DeliverableIntent | None] = ContextVar(
    "agent_deliverable_intent",
    default=None,
)
_deliverable_nudge_count_ctx: ContextVar[int] = ContextVar("agent_deliverable_nudge_count", default=0)


def set_agent_context(
    conversation: Conversation,
    user,
    *,
    deliverable_intent: DeliverableIntent | None = None,
) -> None:
    _conversation_ctx.set(conversation)
    _user_ctx.set(user)
    _deliverable_intent_ctx.set(deliverable_intent)
    _deliverable_nudge_count_ctx.set(0)


def get_agent_conversation() -> Conversation | None:
    return _conversation_ctx.get()


def get_agent_user():
    return _user_ctx.get()


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
