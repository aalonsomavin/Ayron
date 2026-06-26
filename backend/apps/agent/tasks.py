import logging
import time

from celery import shared_task
from langgraph.types import Command
from openai import OpenAIError

from apps.agent.cancellation import AgentCancelledError, clear_cancel, is_cancelled
from apps.agent.checkpoint import agent_config, has_checkpoint, rollback_thread_to_turn
from apps.agent.clarification_interrupt import find_clarification_tool_call, has_clarification_interrupt
from apps.agent.context import set_agent_context
from apps.agent.deliverable_intent import detect_deliverable_intent
from apps.agent.events import persist_event
from apps.agent.runner import create_agent
from apps.agent.streaming import StreamEventHandler
from apps.chat.models import AgentEvent, Conversation, Message
from apps.files.services import get_context_attachments_for_message

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3
LLM_RETRY_MESSAGE = (
    "The language model service returned a temporary error. Please try sending your message again."
)


def format_agent_error(exc: Exception) -> str:
    if isinstance(exc, OpenAIError):
        return LLM_RETRY_MESSAGE
    return str(exc)


def is_recoverable_agent_error(exc: Exception) -> bool:
    return isinstance(exc, OpenAIError)


def stream_agent_response(agent, input_state, config, handler, conversation_id) -> None:
    for chunk in agent.stream(
        input_state,
        config=config,
        stream_mode=["messages"],
        version="v2",
    ):
        handler.handle_chunk(chunk)
        if is_cancelled(conversation_id):
            raise AgentCancelledError()


def build_agent_messages(conversation: Conversation, exclude_message_id: int) -> list[dict]:
    messages = []
    for message in conversation.messages.order_by("created_at"):
        if message.id == exclude_message_id:
            continue
        if message.role == Message.Role.ASSISTANT and not message.content:
            continue
        role = "user" if message.role == Message.Role.USER else "assistant"
        messages.append({"role": role, "content": message.content})
    return messages


def build_stream_input(
    conversation: Conversation,
    user_message: Message,
    assistant_message_id: int,
    *,
    resume_tool_call_id: str = "",
    resume_tool_result: str = "",
) -> tuple[dict | Command, dict]:
    config = agent_config(conversation.id)
    if resume_tool_result:
        input_state = Command(
            resume={
                "decisions": [
                    {
                        "type": "respond",
                        "message": resume_tool_result,
                    }
                ]
            }
        )
    elif has_checkpoint(conversation.id):
        input_state = {"messages": [{"role": "user", "content": user_message.content}]}
    else:
        input_state = {
            "messages": build_agent_messages(
                conversation,
                exclude_message_id=assistant_message_id,
            )
        }
    return input_state, config


def finalize_awaiting_clarification(
    *,
    conversation: Conversation,
    assistant_message: Message,
    handler: StreamEventHandler,
    agent,
    config: dict,
) -> bool:
    state = agent.get_state(config)
    if not has_clarification_interrupt(state):
        return False

    messages = (state.values or {}).get("messages", []) if state else []
    handler.ensure_clarification_event(messages)

    conversation.refresh_from_db()
    if conversation.status != Conversation.Status.PROCESSING:
        return True

    assistant_message.content = handler.get_content()
    assistant_message.save(update_fields=["content"])

    persist_event(
        conversation=conversation,
        event_type=AgentEvent.EventType.DONE,
        payload={"awaiting_clarification": True},
        message=assistant_message,
    )

    conversation.status = Conversation.Status.AWAITING_CLARIFICATION
    conversation.save(update_fields=["status", "updated_at"])
    return True


@shared_task(bind=True)
def run_agent_conversation(
    self,
    conversation_id,
    user_message_id,
    assistant_message_id,
    resume_tool_call_id="",
    resume_tool_result="",
):
    conversation = Conversation.objects.get(id=conversation_id)
    user_message = Message.objects.get(
        id=user_message_id,
        conversation=conversation,
    )
    assistant_message = Message.objects.get(
        id=assistant_message_id,
        conversation=conversation,
    )

    handler = StreamEventHandler(
        conversation=conversation,
        message=assistant_message,
        persist_fn=persist_event,
    )

    clear_cancel(conversation_id)

    agent = None
    try:
        deliverable_intent = detect_deliverable_intent(
            user_message.content,
            context_attachments=get_context_attachments_for_message(user_message),
        )
        set_agent_context(
            conversation,
            conversation.user,
            deliverable_intent=deliverable_intent,
        )
        agent = create_agent(conversation, user_message=user_message)
        input_state, config = build_stream_input(
            conversation,
            user_message,
            assistant_message.id,
            resume_tool_call_id=resume_tool_call_id,
            resume_tool_result=resume_tool_result,
        )

        for attempt in range(1, MAX_LLM_RETRIES + 1):
            try:
                stream_agent_response(agent, input_state, config, handler, conversation_id)
                break
            except OpenAIError:
                can_retry = (
                    attempt < MAX_LLM_RETRIES
                    and not handler.get_content()
                    and not handler.started_tool_calls
                )
                if not can_retry:
                    raise
                logger.warning(
                    "Transient OpenAI error, retrying agent stream",
                    extra={
                        "conversation_id": str(conversation_id),
                        "attempt": attempt,
                        "task_id": self.request.id,
                    },
                )
                time.sleep(min(2**attempt, 10))

        if finalize_awaiting_clarification(
            conversation=conversation,
            assistant_message=assistant_message,
            handler=handler,
            agent=agent,
            config=config,
        ):
            return

        conversation.refresh_from_db()
        if conversation.status != Conversation.Status.PROCESSING:
            return

        assistant_message.content = handler.get_content()
        assistant_message.save(update_fields=["content"])

        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.DONE,
            payload={},
            message=assistant_message,
        )

        conversation.status = Conversation.Status.ACTIVE
        conversation.save(update_fields=["status", "updated_at"])
    except AgentCancelledError:
        conversation.refresh_from_db()
        if conversation.status != Conversation.Status.PROCESSING:
            return

        assistant_message.content = handler.get_content()
        assistant_message.save(update_fields=["content"])

        if agent is not None:
            rollback_thread_to_turn(
                conversation,
                user_message,
                include_user_message=True,
                agent=agent,
            )

        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.DONE,
            payload={"cancelled": True},
            message=assistant_message,
        )

        conversation.status = Conversation.Status.ACTIVE
        conversation.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        logger.exception(
            "Agent conversation failed",
            extra={
                "conversation_id": str(conversation_id),
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
                "task_id": self.request.id,
            },
        )
        if agent is not None:
            rollback_thread_to_turn(
                conversation,
                user_message,
                include_user_message=True,
                agent=agent,
            )

        persist_event(
            conversation=conversation,
            event_type=AgentEvent.EventType.ERROR,
            payload={
                "message": format_agent_error(exc),
                "recoverable": is_recoverable_agent_error(exc),
            },
            message=assistant_message,
        )
        conversation.status = Conversation.Status.FAILED
        conversation.save(update_fields=["status", "updated_at"])
        raise
