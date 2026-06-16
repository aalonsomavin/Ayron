from contextvars import ContextVar

from apps.chat.models import Conversation

_conversation_ctx: ContextVar[Conversation | None] = ContextVar("agent_conversation", default=None)
_user_ctx: ContextVar = ContextVar("agent_user", default=None)


def set_agent_context(conversation: Conversation, user) -> None:
    _conversation_ctx.set(conversation)
    _user_ctx.set(user)


def get_agent_conversation() -> Conversation | None:
    return _conversation_ctx.get()


def get_agent_user():
    return _user_ctx.get()
