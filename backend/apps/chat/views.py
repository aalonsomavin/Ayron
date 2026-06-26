import json
import random
from uuid import UUID

from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.agent.cancellation import clear_cancel, request_cancel
from apps.agent.checkpoint import get_checkpointer, rollback_thread_to_turn
from apps.agent.events import get_redis_client, persist_event
from apps.agent.tools.display import TOOL_ICONS, TOOL_LABELS, TOOL_TAGS, get_tool_display
from apps.agent.tools.chart import prepare_chart_for_render
from apps.agent.tools.table import prepare_table_for_render
from apps.agent.tasks import run_agent_conversation
from apps.chat.models import AgentEvent, Conversation, Message
from apps.chat.clarification import (
    apply_step_navigation,
    bad_request,
    build_wizard_context,
    enqueue_clarification_resume,
    get_clarification_event,
    load_wizard_state,
    parse_wizard_request,
    pending_clarification_assistant_message,
    validate_final_answers,
)
from apps.agent.tools.clarification import (
    format_clarification_tool_result,
    merge_step_answer,
    parse_step_answer_from_post,
)
from apps.files.services import hydrate_file_payload_for_ui
from apps.chat.tool_trace import tool_trace_for_message
from config.celery import app as celery_app


HERO_TITLES = (
    "¿Qué quieres saber hoy?",
    "¿Qué te gustaría explorar?",
    "¿Qué pregunta tenés?",
    "¿En qué te ayudo?",
    "¿Qué buscamos hoy?",
    "¿Qué necesitás saber?",
    "¿Por dónde empezamos?",
    "¿Qué resolvemos hoy?",
    "¿Qué te interesa saber?",
    "¿Qué armamos hoy?",
    "¿Qué revisamos juntos?",
    "¿Qué comparamos?",
    "¿Qué te traés hoy?",
    "¿Qué miramos?",
    "¿Qué descubrimos hoy?",
)


def _user_display_name(user) -> str:
    full_name = user.get_full_name().strip()
    if full_name:
        name = full_name.split()[0]
    else:
        name = user.get_username()
    if not name:
        return name
    return name[0].upper() + name[1:]


def _hero_title(user) -> str:
    name = _user_display_name(user)
    options = list(HERO_TITLES) + [
        f"¡Hola, {name}!",
        f"¡Hola, {name}! ¿qué hacemos?",
        f"¿Qué hacemos hoy, {name}?",
        f"¡Hola, {name}! ¿en qué te ayudo?",
    ]
    return random.choice(options)


def _get_conversation(request, conversation_id):
    return get_object_or_404(Conversation, id=conversation_id, user=request.user)


def serialize_agent_event(event: AgentEvent, *, user=None) -> dict:
    data = {
        "seq": event.sequence_number,
        "type": event.event_type,
        **event.payload,
    }
    if event.message_id:
        data["message_id"] = event.message_id

    if event.event_type in (
        AgentEvent.EventType.TOOL_START,
        AgentEvent.EventType.TOOL_END,
    ):
        tool_name = data.get("tool")
        if tool_name:
            tool_input = data.get("input") if event.event_type == AgentEvent.EventType.TOOL_START else None
            data.update(get_tool_display(tool_name, tool_input))

    if event.event_type in (
        AgentEvent.EventType.FILE_CREATED,
        AgentEvent.EventType.FILE_UPDATED,
    ):
        data.update(
            hydrate_file_payload_for_ui(
                data,
                conversation_id=event.conversation_id,
                user=user,
            )
        )

    if event.event_type == AgentEvent.EventType.PLAN:
        data.setdefault("tool", "write_todos")
        data.update(get_tool_display("write_todos", {"todos": data.get("todos")}))

    return data


def _conversation_last_sequence(conversation: Conversation) -> int:
    result = AgentEvent.objects.filter(conversation=conversation).aggregate(
        max_seq=Max("sequence_number")
    )
    max_seq = result["max_seq"]
    return max_seq if max_seq is not None else -1


def _active_message_id(conversation: Conversation) -> int | None:
    if conversation.status != Conversation.Status.PROCESSING:
        return None
    message = (
        conversation.messages.filter(role=Message.Role.ASSISTANT, content="")
        .order_by("-created_at")
        .first()
    )
    return message.id if message else None


def _sidebar_conversations(request):
    return Conversation.objects.filter(user=request.user).order_by("-updated_at")[:50]


def _user_initials(user) -> str:
    name = user.get_full_name().strip() or user.get_username()
    parts = [part for part in name.split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


def _content_blocks_for_message(message: Message, *, user=None) -> list[dict]:
    events = AgentEvent.objects.filter(message=message).order_by("sequence_number")

    blocks: list[dict] = []
    can_merge_token = False
    for event in events:
        if event.event_type == AgentEvent.EventType.TOKEN:
            chunk = event.payload.get("content", "")
            if not chunk:
                continue
            if can_merge_token and blocks and blocks[-1]["type"] == "text":
                blocks[-1]["content"] += chunk
            else:
                blocks.append({"type": "text", "content": chunk})
            can_merge_token = True
        elif event.event_type == AgentEvent.EventType.TABLE:
            blocks.append(
                {
                    "type": "table",
                    "table": prepare_table_for_render(event.payload),
                }
            )
            can_merge_token = False
        elif event.event_type == AgentEvent.EventType.CHART:
            chart = prepare_chart_for_render(event.payload)
            blocks.append(
                {
                    "type": "chart",
                    "chart": chart,
                    "chart_id": f"chart-{message.id}-{len(blocks)}",
                }
            )
            can_merge_token = False
        elif event.event_type == AgentEvent.EventType.CLARIFICATION:
            payload = dict(event.payload)
            tool_call_id = payload.get("tool_call_id", "")
            answers = payload.get("answers") or {}
            blocks.append(
                {
                    "type": "clarification",
                    **build_wizard_context(
                        conversation=message.conversation,
                        payload=payload,
                        assistant_message_id=message.id,
                        tool_call_id=tool_call_id,
                        step=0,
                        answers=answers,
                    ),
                }
            )
            can_merge_token = False
        elif event.event_type in (
            AgentEvent.EventType.FILE_CREATED,
            AgentEvent.EventType.FILE_UPDATED,
        ):
            file_payload = hydrate_file_payload_for_ui(
                dict(event.payload),
                conversation_id=message.conversation_id,
                user=user,
            )
            if blocks and blocks[-1]["type"] == "files":
                blocks[-1]["files"].append(file_payload)
            else:
                blocks.append({"type": "files", "files": [file_payload]})
            can_merge_token = False
        else:
            can_merge_token = False

    if blocks and message.content and not any(block["type"] == "text" for block in blocks):
        blocks.insert(0, {"type": "text", "content": message.content})
    elif not blocks and message.content:
        blocks.append({"type": "text", "content": message.content})

    return blocks


def _message_was_cancelled(message: Message) -> bool:
    return AgentEvent.objects.filter(
        message=message,
        event_type=AgentEvent.EventType.DONE,
        payload__cancelled=True,
    ).exists()


def _user_message_for_assistant(assistant_message: Message) -> Message | None:
    return (
        Message.objects.filter(
            conversation_id=assistant_message.conversation_id,
            role=Message.Role.USER,
            created_at__lt=assistant_message.created_at,
        )
        .order_by("-created_at")
        .first()
    )


def _messages_with_content_blocks(conversation: Conversation) -> list[Message]:
    messages = list(conversation.messages.select_related().order_by("created_at"))
    for message in messages:
        if message.role == Message.Role.ASSISTANT:
            message.content_blocks = _content_blocks_for_message(message, user=conversation.user)
            message.tool_trace = tool_trace_for_message(message)
            message.cancelled = _message_was_cancelled(message)
    return messages


def _chat_turns(messages: list[Message]) -> list[dict]:
    turns: list[dict] = []
    current: dict | None = None

    for message in messages:
        if message.role == Message.Role.USER and message.content:
            if current is not None:
                turns.append(current)
            current = {"user": message, "assistant": None}
        elif message.role == Message.Role.ASSISTANT and current is not None:
            current["assistant"] = message

    if current is not None:
        turns.append(current)

    return turns


def _enqueue_user_message(conversation: Conversation, content: str) -> tuple[Message, Message]:
    user_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=content,
    )
    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content="",
    )

    update_fields = ["status", "updated_at", "celery_task_id"]
    if not conversation.title:
        conversation.title = content[:255]
        update_fields.append("title")

    conversation.status = Conversation.Status.PROCESSING
    clear_cancel(conversation.id)
    task = run_agent_conversation.delay(
        str(conversation.id),
        user_message.id,
        assistant_message.id,
    )
    conversation.celery_task_id = task.id
    conversation.save(update_fields=update_fields)
    return user_message, assistant_message


def _aggregate_message_content(message: Message) -> str:
    parts = []
    for event in AgentEvent.objects.filter(
        message=message,
        event_type=AgentEvent.EventType.TOKEN,
    ).order_by("sequence_number"):
        chunk = event.payload.get("content", "")
        if chunk:
            parts.append(chunk)
    return "".join(parts)


def _finalize_clarification_cancel(conversation: Conversation) -> bool:
    conversation.refresh_from_db()
    if conversation.status != Conversation.Status.AWAITING_CLARIFICATION:
        return False

    assistant_message = pending_clarification_assistant_message(conversation)
    if assistant_message is None:
        conversation.status = Conversation.Status.ACTIVE
        conversation.save(update_fields=["status", "updated_at"])
        return True

    user_message = _user_message_for_assistant(assistant_message)
    if user_message is not None:
        rollback_thread_to_turn(
            conversation,
            user_message,
            include_user_message=True,
        )

    content = _aggregate_message_content(assistant_message)
    if content:
        assistant_message.content = content
        assistant_message.save(update_fields=["content"])

    persist_event(
        conversation=conversation,
        event_type=AgentEvent.EventType.DONE,
        payload={"cancelled": True},
        message=assistant_message,
    )
    conversation.status = Conversation.Status.ACTIVE
    conversation.save(update_fields=["status", "updated_at"])
    return True


def _finalize_cancelled_conversation(conversation: Conversation) -> bool:
    conversation.refresh_from_db()
    if conversation.status != Conversation.Status.PROCESSING:
        return False

    assistant_message_id = _active_message_id(conversation)
    if assistant_message_id is None:
        conversation.status = Conversation.Status.ACTIVE
        conversation.save(update_fields=["status", "updated_at"])
        return True

    assistant_message = Message.objects.get(id=assistant_message_id, conversation=conversation)
    content = _aggregate_message_content(assistant_message)
    if content:
        assistant_message.content = content
        assistant_message.save(update_fields=["content"])

    user_message = _user_message_for_assistant(assistant_message)
    if user_message is not None:
        rollback_thread_to_turn(
            conversation,
            user_message,
            include_user_message=True,
        )

    persist_event(
        conversation=conversation,
        event_type=AgentEvent.EventType.DONE,
        payload={"cancelled": True},
        message=assistant_message,
    )
    conversation.status = Conversation.Status.ACTIVE
    conversation.save(update_fields=["status", "updated_at"])
    return True


@require_GET
def conversation_list(request):
    return render(
        request,
        "chat/list.html",
        {
            "conversations": _sidebar_conversations(request),
            "new_chat_active": True,
            "active_conversation_id": None,
            "hero_title": _hero_title(request.user),
        },
    )


@require_GET
def conversation_new(request):
    return redirect("chat:list")


@require_POST
def conversation_start(request):
    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponseBadRequest("Message content is required.")

    conversation = Conversation.objects.create(user=request.user)
    _enqueue_user_message(conversation, content)
    return redirect("chat:detail", conversation_id=conversation.id)


@require_GET
def conversation_detail(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    chat_messages = _messages_with_content_blocks(conversation)
    active_id = _active_message_id(conversation)
    if active_id:
        for message in chat_messages:
            if message.id == active_id:
                message.content_blocks = []
                message.tool_trace = None
                break
    return render(
        request,
        "chat/detail.html",
        {
            "conversation": conversation,
            "chat_messages": chat_messages,
            "chat_turns": _chat_turns(chat_messages),
            "conversations": _sidebar_conversations(request),
            "new_chat_active": False,
            "active_conversation_id": conversation.id,
            "last_sequence": _conversation_last_sequence(conversation),
            "active_message_id": _active_message_id(conversation),
            "tool_labels_json": json.dumps(TOOL_LABELS),
            "tool_tags_json": json.dumps(TOOL_TAGS),
            "tool_icons_json": json.dumps(TOOL_ICONS),
            "user_initials": _user_initials(request.user),
        },
    )


@require_POST
def send_message(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    if conversation.status == Conversation.Status.PROCESSING:
        return HttpResponseBadRequest("Conversation is already processing a message.")

    if conversation.status == Conversation.Status.AWAITING_CLARIFICATION:
        return HttpResponseBadRequest("Complete or skip the clarification request first.")

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponseBadRequest("Message content is required.")

    user_message, assistant_message = _enqueue_user_message(conversation, content)

    if request.headers.get("HX-Request"):
        return JsonResponse(
            {
                "assistant_message_id": assistant_message.id,
                "last_sequence": _conversation_last_sequence(conversation),
            }
        )

    return redirect("chat:detail", conversation_id=conversation.id)


@require_POST
def stop_conversation(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    if conversation.status == Conversation.Status.AWAITING_CLARIFICATION:
        _finalize_clarification_cancel(conversation)
        return HttpResponse(status=204)

    if conversation.status != Conversation.Status.PROCESSING:
        return HttpResponseBadRequest("Conversation is not processing a message.")

    request_cancel(conversation.id)
    _finalize_cancelled_conversation(conversation)
    if conversation.celery_task_id:
        celery_app.control.revoke(conversation.celery_task_id, terminate=True)

    return HttpResponse(status=204)


@require_POST
def retry_message(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    if conversation.status == Conversation.Status.PROCESSING:
        return HttpResponseBadRequest("Conversation is already processing a message.")

    assistant_param = request.POST.get("assistant_message_id")
    if not assistant_param:
        return HttpResponseBadRequest("Assistant message id is required.")

    try:
        assistant_message_id = int(assistant_param)
    except ValueError:
        return HttpResponseBadRequest("Invalid assistant message id.")

    assistant_message = get_object_or_404(
        Message,
        id=assistant_message_id,
        conversation=conversation,
        role=Message.Role.ASSISTANT,
    )

    if not _message_was_cancelled(assistant_message):
        return HttpResponseBadRequest("Message was not cancelled.")

    user_message = _user_message_for_assistant(assistant_message)
    if user_message is None:
        return HttpResponseBadRequest("User message not found.")

    AgentEvent.objects.filter(message=assistant_message).delete()
    assistant_message.content = ""
    assistant_message.save(update_fields=["content"])

    rollback_thread_to_turn(
        conversation,
        user_message,
        include_user_message=False,
    )

    update_fields = ["status", "updated_at", "celery_task_id"]
    conversation.status = Conversation.Status.PROCESSING
    clear_cancel(conversation.id)
    task = run_agent_conversation.delay(
        str(conversation.id),
        user_message.id,
        assistant_message.id,
    )
    conversation.celery_task_id = task.id
    conversation.save(update_fields=update_fields)

    return JsonResponse(
        {
            "assistant_message_id": assistant_message.id,
            "last_sequence": _conversation_last_sequence(conversation),
        }
    )


@require_GET
def events_replay(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    after_param = request.GET.get("after")
    events_qs = AgentEvent.objects.filter(conversation=conversation).order_by("sequence_number")
    if after_param is not None and after_param != "":
        try:
            after = int(after_param)
        except ValueError:
            return HttpResponseBadRequest("Invalid after parameter.")
        events_qs = events_qs.filter(sequence_number__gt=after)

    events = [serialize_agent_event(event, user=request.user) for event in events_qs]
    last_sequence = _conversation_last_sequence(conversation)

    return JsonResponse(
        {
            "events": events,
            "last_sequence": last_sequence,
            "status": conversation.status,
            "has_more": False,
        }
    )


def _format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


@require_GET
def event_stream(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    try:
        after = int(request.GET.get("after", -1))
    except ValueError:
        return HttpResponseBadRequest("Invalid after parameter.")

    conversation_id_str = str(conversation.id)
    channel = f"conversation:{conversation_id_str}"

    def generate():
        pubsub = get_redis_client().pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        last_seq = after
        try:
            while True:
                message = pubsub.get_message(timeout=30.0)
                if message is None:
                    yield ": heartbeat\n\n"
                    conversation.refresh_from_db()
                    if conversation.status != Conversation.Status.PROCESSING:
                        break
                    continue

                if message.get("type") != "message":
                    continue

                data = json.loads(message["data"])
                seq = data.get("seq")
                if seq is None or seq <= last_seq:
                    continue

                event_type = data.get("type", "message")
                yield _format_sse(event_type, data)
                last_seq = seq

                if event_type in (AgentEvent.EventType.DONE, AgentEvent.EventType.ERROR):
                    break
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    response = StreamingHttpResponse(generate(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _render_clarification_partial(request, context: dict):
    wrapped = {"clarification": context}
    if context.get("submitted"):
        template = "chat/partials/clarification_dismissed.html"
    else:
        template = "chat/partials/clarification_wizard.html"
    return render(request, template, wrapped)


def _clarification_oob_response(request, context: dict, *, trigger: dict | None = None):
    response = _render_clarification_partial(request, context)
    if context.get("submitted"):
        response["HX-Reswap"] = "delete"
    if trigger:
        response["HX-Trigger"] = json.dumps(trigger)
    return response


@require_GET
def clarification_wizard(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    try:
        assistant_message_id, tool_call_id, step, answers, _answers_json = parse_wizard_request(
            request
        )
    except ValueError as exc:
        return bad_request(str(exc))

    event = get_clarification_event(conversation, assistant_message_id, tool_call_id)
    if event is None:
        return bad_request("Clarification request not found")

    payload = dict(event.payload)
    if payload.get("submitted"):
        context = build_wizard_context(
            conversation=conversation,
            payload=payload,
            assistant_message_id=assistant_message_id,
            tool_call_id=tool_call_id,
            step=0,
            answers=payload.get("answers") or {},
        )
        return _render_clarification_partial(request, context)

    if conversation.status != Conversation.Status.AWAITING_CLARIFICATION:
        return bad_request("Conversation is not awaiting clarification")

    context = build_wizard_context(
        conversation=conversation,
        payload=payload,
        assistant_message_id=assistant_message_id,
        tool_call_id=tool_call_id,
        step=step,
        answers=answers,
    )
    return _render_clarification_partial(request, context)


@require_POST
def clarification_step(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    try:
        assistant_message_id, tool_call_id, step, answers, _answers_json = parse_wizard_request(
            request
        )
        _event, payload = load_wizard_state(conversation, assistant_message_id, tool_call_id)
        direction = (request.POST.get("direction") or "next").strip().lower()
        if direction not in {"next", "back"}:
            return bad_request("Invalid direction")
        step, answers = apply_step_navigation(
            payload=payload,
            step=step,
            answers=answers,
            post_data=request.POST,
            direction=direction,
        )
    except ValueError as exc:
        return bad_request(str(exc))

    context = build_wizard_context(
        conversation=conversation,
        payload=payload,
        assistant_message_id=assistant_message_id,
        tool_call_id=tool_call_id,
        step=step,
        answers=answers,
    )
    return _render_clarification_partial(request, context)


@require_POST
def clarification_submit(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    try:
        assistant_message_id, tool_call_id, step, answers, _answers_json = parse_wizard_request(
            request
        )
        event, payload = load_wizard_state(conversation, assistant_message_id, tool_call_id)
        skipped = request.POST.get("skipped") == "1"
        assistant_message = Message.objects.get(
            id=assistant_message_id,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
        )

        if skipped:
            if not payload.get("allow_skip", True):
                return bad_request("Skip is not allowed")
            final_answers = None
        else:
            questions = payload.get("questions", [])
            if questions:
                last_question = questions[min(step, len(questions) - 1)]
                step_answer = parse_step_answer_from_post(last_question, request.POST)
                answers = merge_step_answer(answers, last_question["id"], step_answer)
            final_answers = validate_final_answers(payload, answers)

        tool_result = format_clarification_tool_result(
            payload,
            final_answers,
            skipped=skipped,
        )

        updated_payload = {
            **payload,
            "submitted": True,
            "skipped": skipped,
            "answers": final_answers,
        }
        event.payload = updated_payload
        event.save(update_fields=["payload"])

        enqueue_clarification_resume(
            conversation,
            assistant_message,
            tool_call_id=tool_call_id,
            tool_result=tool_result,
        )

        context = build_wizard_context(
            conversation=conversation,
            payload=updated_payload,
            assistant_message_id=assistant_message_id,
            tool_call_id=tool_call_id,
            step=0,
            answers=final_answers or {},
        )
        return _clarification_oob_response(
            request,
            context,
            trigger={
                "ayronResumeStream": {
                    "assistant_message_id": assistant_message_id,
                    "last_sequence": _conversation_last_sequence(conversation),
                }
            },
        )
    except ValueError as exc:
        return bad_request(str(exc))
    except Message.DoesNotExist:
        return bad_request("Assistant message not found")


@require_POST
def conversation_rename(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return HttpResponseBadRequest("Title is required.")
    conversation.title = title[:255]
    conversation.save(update_fields=["title", "updated_at"])

    active_param = (request.POST.get("active_conversation_id") or "").strip()
    active_conversation_id = None
    if active_param:
        try:
            active_conversation_id = UUID(active_param)
        except ValueError:
            pass

    return render(
        request,
        "chat/sidebar_conversation_item.html",
        {
            "item": conversation,
            "active_conversation_id": active_conversation_id,
        },
    )


@require_POST
def conversation_delete(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    is_active = request.POST.get("active") == "1"

    if conversation.status == Conversation.Status.PROCESSING:
        request_cancel(conversation.id)
        _finalize_cancelled_conversation(conversation)
        conversation.refresh_from_db()
        if conversation.celery_task_id:
            celery_app.control.revoke(conversation.celery_task_id, terminate=True)

    try:
        get_checkpointer().delete_thread(str(conversation.id))
    except Exception:
        pass

    conversation.delete()

    response = HttpResponse(status=200)
    response["HX-Trigger"] = json.dumps({"ayronToast": {"message": "Chat eliminado"}})
    if is_active:
        response["HX-Redirect"] = reverse("chat:list")
    return response
