from urllib.parse import quote_plus
from uuid import UUID

from django.conf import settings
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from apps.chat.models import Conversation, Message

_checkpointer = None
_checkpointer_override = None
_checkpointer_setup_done = False


def set_checkpointer(checkpointer) -> None:
    global _checkpointer_override
    _checkpointer_override = checkpointer


def reset_checkpointer() -> None:
    global _checkpointer, _checkpointer_override
    _checkpointer = None
    _checkpointer_override = None


def _uses_sqlite() -> bool:
    engine = settings.DATABASES["default"]["ENGINE"]
    return "sqlite" in engine


def _build_postgres_conn_string() -> str:
    db = settings.DATABASES["default"]
    user = db["USER"]
    password = db.get("PASSWORD") or ""
    host = db.get("HOST") or "localhost"
    port = db.get("PORT") or 5432
    name = db["NAME"]
    if password:
        auth = f"{quote_plus(user)}:{quote_plus(password)}@"
    else:
        auth = f"{quote_plus(user)}@"
    return f"postgresql://{auth}{host}:{port}/{name}"


def get_checkpointer():
    global _checkpointer, _checkpointer_setup_done
    if _checkpointer_override is not None:
        return _checkpointer_override
    if _checkpointer is not None:
        return _checkpointer
    if _uses_sqlite():
        _checkpointer = MemorySaver()
        return _checkpointer
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    conn_string = _build_postgres_conn_string()
    pool = ConnectionPool(
        conninfo=conn_string,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
    )
    _checkpointer = PostgresSaver(pool)
    if not _checkpointer_setup_done:
        _checkpointer.setup()
        _checkpointer_setup_done = True
    return _checkpointer


def setup_checkpointer() -> None:
    checkpointer = get_checkpointer()
    if hasattr(checkpointer, "setup"):
        checkpointer.setup()


def agent_config(conversation_id: UUID | str) -> dict:
    return {"configurable": {"thread_id": str(conversation_id)}}


def has_checkpoint(conversation_id: UUID | str) -> bool:
    checkpointer = get_checkpointer()
    config = agent_config(conversation_id)
    checkpoint_tuple = checkpointer.get_tuple(config)
    return checkpoint_tuple is not None


def _is_human_message(message) -> bool:
    if isinstance(message, HumanMessage):
        return True
    if isinstance(message, dict):
        role = message.get("role")
        msg_type = message.get("type")
        return role == "user" or msg_type == "human"
    msg_type = getattr(message, "type", None)
    return msg_type == "human"


def user_message_turn_index(conversation: Conversation, user_message: Message) -> int:
    user_ids = list(
        conversation.messages.filter(role=Message.Role.USER)
        .order_by("created_at")
        .values_list("id", flat=True)
    )
    return user_ids.index(user_message.id)


def trim_messages_to_user_turn(messages: list, user_turn_index: int) -> list:
    human_seen = -1
    cut_at = 0
    for index, message in enumerate(messages):
        if _is_human_message(message):
            human_seen += 1
            if human_seen == user_turn_index:
                cut_at = index + 1
                break
    return messages[:cut_at] if cut_at else []


def trim_messages_before_user_turn(messages: list, user_turn_index: int) -> list:
    human_seen = -1
    for index, message in enumerate(messages):
        if _is_human_message(message):
            human_seen += 1
            if human_seen == user_turn_index:
                return messages[:index]
    return messages


def rollback_thread_to_turn(
    conversation: Conversation,
    user_message: Message,
    *,
    include_user_message: bool = True,
    agent=None,
) -> None:
    thread_id = str(conversation.id)
    if not has_checkpoint(thread_id):
        return

    if agent is None:
        from apps.agent.runner import create_agent

        agent = create_agent(conversation, user_message=user_message)

    config = agent_config(thread_id)
    state = agent.get_state(config)
    if not state or not state.values:
        return

    messages = state.values.get("messages") or []
    if not messages:
        get_checkpointer().delete_thread(thread_id)
        return

    turn_index = user_message_turn_index(conversation, user_message)
    if include_user_message:
        trimmed = trim_messages_to_user_turn(messages, turn_index)
    else:
        trimmed = trim_messages_before_user_turn(messages, turn_index)

    checkpointer = get_checkpointer()
    if not trimmed:
        checkpointer.delete_thread(thread_id)
        return

    agent.update_state(config, {"messages": trimmed})
