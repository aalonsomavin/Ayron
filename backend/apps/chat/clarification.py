import json

from django.http import HttpResponseBadRequest

from apps.agent.tasks import run_agent_conversation
from apps.agent.tools.clarification import (
    format_clarification_summary,
    format_clarification_tool_result,
    merge_step_answer,
    parse_answers_json,
    parse_step_answer_from_post,
    validate_step_answer,
)
from apps.chat.models import AgentEvent, Conversation, Message


def get_clarification_event(
    conversation: Conversation,
    assistant_message_id: int,
    tool_call_id: str | None = None,
) -> AgentEvent | None:
    events = AgentEvent.objects.filter(
        conversation=conversation,
        message_id=assistant_message_id,
        event_type=AgentEvent.EventType.CLARIFICATION,
    ).order_by("-sequence_number")
    if tool_call_id:
        for event in events:
            if event.payload.get("tool_call_id") == tool_call_id:
                return event
        return None
    return events.first()


def clarification_payload(event: AgentEvent) -> dict:
    return dict(event.payload)


def pending_clarification_assistant_message(conversation: Conversation) -> Message | None:
    if conversation.status != Conversation.Status.AWAITING_CLARIFICATION:
        return None
    event = (
        AgentEvent.objects.filter(
            conversation=conversation,
            event_type=AgentEvent.EventType.CLARIFICATION,
            payload__submitted=False,
        )
        .order_by("-sequence_number")
        .first()
    )
    if not event or not event.message_id:
        return None
    return Message.objects.filter(
        id=event.message_id,
        conversation=conversation,
        role=Message.Role.ASSISTANT,
    ).first()


def build_wizard_context(
    *,
    conversation: Conversation,
    payload: dict,
    assistant_message_id: int,
    tool_call_id: str,
    step: int,
    answers: dict,
) -> dict:
    questions = payload.get("questions", [])
    total_steps = len(questions)
    step = max(0, min(step, max(total_steps - 1, 0)))
    question = questions[step] if questions else None
    current_answer = answers.get(question["id"]) if question else None
    can_go_next = True
    if question and not question.get("optional"):
        try:
            validate_step_answer(question, current_answer)
        except ValueError:
            can_go_next = False

    is_last_step = step >= total_steps - 1 if total_steps else True
    next_label = payload.get("submit_label", "Analizar con esto") if is_last_step else "Siguiente"

    return {
        "conversation": conversation,
        "assistant_message_id": assistant_message_id,
        "tool_call_id": tool_call_id,
        "payload": payload,
        "questions": questions,
        "step": step,
        "total_steps": total_steps,
        "question": question,
        "answers": answers,
        "answers_json": json.dumps(answers, ensure_ascii=False),
        "allow_skip": bool(payload.get("allow_skip", True)),
        "submit_label": payload.get("submit_label", "Analizar con esto"),
        "submitted": bool(payload.get("submitted", False)),
        "skipped": bool(payload.get("skipped", False)),
        "summary": format_clarification_summary(payload, answers, payload.get("skipped", False)),
        "can_go_back": step > 0,
        "can_go_next": can_go_next,
        "is_last_step": is_last_step,
        "next_label": next_label,
        "current_answer": current_answer or {},
    }


def parse_wizard_request(request) -> tuple[int, str, int, dict, str]:
    assistant_param = request.GET.get("assistant_message_id") or request.POST.get(
        "assistant_message_id"
    )
    tool_call_id = (request.GET.get("tool_call_id") or request.POST.get("tool_call_id") or "").strip()
    step_param = request.GET.get("step") or request.POST.get("step") or "0"
    answers_json = request.GET.get("answers_json") or request.POST.get("answers_json") or "{}"

    if not assistant_param:
        raise ValueError("assistant_message_id is required")
    if not tool_call_id:
        raise ValueError("tool_call_id is required")

    try:
        assistant_message_id = int(assistant_param)
    except ValueError as exc:
        raise ValueError("Invalid assistant_message_id") from exc

    try:
        step = int(step_param)
    except ValueError as exc:
        raise ValueError("Invalid step") from exc

    return assistant_message_id, tool_call_id, step, parse_answers_json(answers_json), answers_json


def load_wizard_state(conversation: Conversation, assistant_message_id: int, tool_call_id: str):
    if conversation.status != Conversation.Status.AWAITING_CLARIFICATION:
        raise ValueError("Conversation is not awaiting clarification")

    event = get_clarification_event(conversation, assistant_message_id, tool_call_id)
    if event is None:
        raise ValueError("Clarification request not found")

    payload = clarification_payload(event)
    if payload.get("submitted"):
        raise ValueError("Clarification already submitted")

    return event, payload


def enqueue_clarification_resume(
    conversation: Conversation,
    assistant_message: Message,
    *,
    tool_call_id: str,
    tool_result: str,
) -> None:
    user_message = (
        Message.objects.filter(
            conversation=conversation,
            role=Message.Role.USER,
            created_at__lt=assistant_message.created_at,
        )
        .order_by("-created_at")
        .first()
    )
    if user_message is None:
        raise ValueError("User message not found")

    conversation.status = Conversation.Status.PROCESSING
    task = run_agent_conversation.delay(
        str(conversation.id),
        user_message.id,
        assistant_message.id,
        resume_tool_call_id=tool_call_id,
        resume_tool_result=tool_result,
    )
    conversation.celery_task_id = task.id
    conversation.save(update_fields=["status", "updated_at", "celery_task_id"])


def bad_request(message: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(message)


def apply_step_navigation(
    *,
    payload: dict,
    step: int,
    answers: dict,
    post_data,
    direction: str,
) -> tuple[int, dict]:
    questions = payload.get("questions", [])
    if not questions:
        raise ValueError("No clarification questions found")

    step = max(0, min(step, len(questions) - 1))
    question = questions[step]
    step_answer = parse_step_answer_from_post(question, post_data)
    answers = merge_step_answer(answers, question["id"], step_answer)

    if direction == "back":
        return max(step - 1, 0), answers

    validate_step_answer(question, step_answer)
    if step >= len(questions) - 1:
        return step, answers
    return step + 1, answers


def validate_final_answers(payload: dict, answers: dict) -> dict:
    validated = {}
    for question in payload.get("questions", []):
        answer = answers.get(question["id"], {})
        validated[question["id"]] = validate_step_answer(question, answer)
    return validated
