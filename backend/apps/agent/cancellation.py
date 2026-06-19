from uuid import UUID

from apps.agent.events import get_redis_client

CANCEL_TTL_SECONDS = 3600


class AgentCancelledError(Exception):
    pass


def _cancel_key(conversation_id: UUID | str) -> str:
    return f"conversation:{conversation_id}:cancel"


def request_cancel(conversation_id: UUID | str) -> None:
    get_redis_client().set(_cancel_key(conversation_id), "1", ex=CANCEL_TTL_SECONDS)


def is_cancelled(conversation_id: UUID | str) -> bool:
    return bool(get_redis_client().get(_cancel_key(conversation_id)))


def clear_cancel(conversation_id: UUID | str) -> None:
    get_redis_client().delete(_cancel_key(conversation_id))


def check_agent_not_cancelled() -> None:
    from apps.agent.context import get_agent_conversation

    conversation = get_agent_conversation()
    if conversation is not None and is_cancelled(conversation.id):
        raise AgentCancelledError()
