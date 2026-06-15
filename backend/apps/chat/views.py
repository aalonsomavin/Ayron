import json

from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.agent.events import get_redis_client
from apps.agent.tasks import run_agent_conversation
from apps.chat.models import AgentEvent, Conversation, Message


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


@require_GET
def conversation_list(request):
    conversations = _sidebar_conversations(request)
    return render(request, "chat/list.html", {"conversations": conversations})


@require_POST
def conversation_new(request):
    conversation = Conversation.objects.create(user=request.user)
    return redirect("chat:detail", conversation_id=conversation.id)


@require_GET
def conversation_detail(request, conversation_id):
    conversation = _get_conversation(request, conversation_id)
    messages = conversation.messages.select_related().order_by("created_at")
    return render(
        request,
        "chat/detail.html",
        {
            "conversation": conversation,
            "messages": messages,
            "conversations": _sidebar_conversations(request),
            "last_sequence": _conversation_last_sequence(conversation),
            "active_message_id": _active_message_id(conversation),
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
