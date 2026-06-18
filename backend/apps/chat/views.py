import json
import random

from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.agent.events import get_redis_client
from apps.agent.tools.display import PLAN_TOOL_LABEL, TOOL_LABELS, get_tool_display
from apps.agent.tools.chart import prepare_chart_for_render
from apps.agent.tools.table import prepare_table_for_render
from apps.agent.tasks import run_agent_conversation
from apps.chat.models import AgentEvent, Conversation, Message
from apps.chat.tool_trace import tool_trace_for_message


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


def serialize_agent_event(event: AgentEvent) -> dict:
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

    if event.event_type == AgentEvent.EventType.PLAN:
        data.setdefault("tool_label", PLAN_TOOL_LABEL)
        data.setdefault("tool", "write_todos")

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


def _content_blocks_for_message(message: Message) -> list[dict]:
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
        elif event.event_type in (
            AgentEvent.EventType.FILE_CREATED,
            AgentEvent.EventType.FILE_UPDATED,
        ):
            file_payload = dict(event.payload)
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


def _messages_with_content_blocks(conversation: Conversation) -> list[Message]:
    messages = list(conversation.messages.select_related().order_by("created_at"))
    for message in messages:
        if message.role == Message.Role.ASSISTANT:
            message.content_blocks = _content_blocks_for_message(message)
            message.tool_trace = tool_trace_for_message(message)
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
    task = run_agent_conversation.delay(
        str(conversation.id),
        user_message.id,
        assistant_message.id,
    )
    conversation.celery_task_id = task.id
    conversation.save(update_fields=update_fields)
    return user_message, assistant_message


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
            "user_initials": _user_initials(request.user),
        },
    )


@require_POST
def send_message(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)

    if conversation.status == Conversation.Status.PROCESSING:
        return HttpResponseBadRequest("Conversation is already processing a message.")

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponseBadRequest("Message content is required.")

    _enqueue_user_message(conversation, content)

    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)

    return redirect("chat:detail", conversation_id=conversation.id)


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

    events = [serialize_agent_event(event) for event in events_qs]
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
