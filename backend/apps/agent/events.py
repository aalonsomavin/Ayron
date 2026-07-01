import json
from uuid import UUID

import redis
from django.conf import settings
from django.db import transaction
from django.db.models import Max

from apps.chat.models import AgentEvent, Conversation, Message
from apps.files.services import hydrate_file_payload_for_ui

_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client


def build_event_message(
    seq: int,
    event_type: str,
    payload: dict,
    message_id: int | None,
) -> dict:
    message = {
        "seq": seq,
        "type": event_type,
        **payload,
    }
    if message_id is not None:
        message["message_id"] = message_id
    return message


def publish_event(conversation_id: UUID, event_message: dict) -> None:
    channel = f"conversation:{conversation_id}"
    get_redis_client().publish(channel, json.dumps(event_message, default=str))


def next_sequence_number(conversation: Conversation) -> int:
    current_max = AgentEvent.objects.filter(conversation=conversation).aggregate(
        max_seq=Max("sequence_number")
    )["max_seq"]
    return (current_max if current_max is not None else -1) + 1


@transaction.atomic
def persist_event(
    conversation: Conversation,
    event_type: str,
    payload: dict,
    message: Message | None,
) -> tuple[int, AgentEvent]:
    stored_payload = dict(payload)
    if event_type in (
        AgentEvent.EventType.FILE_CREATED,
        AgentEvent.EventType.FILE_UPDATED,
    ):
        stored_payload = hydrate_file_payload_for_ui(
            stored_payload,
            conversation_id=conversation.id,
        )
    seq = next_sequence_number(conversation)
    event = AgentEvent.objects.create(
        conversation=conversation,
        message=message,
        event_type=event_type,
        payload=stored_payload,
        sequence_number=seq,
    )
    event_message = build_event_message(
        seq=seq,
        event_type=event_type,
        payload=stored_payload,
        message_id=message.id if message else None,
    )
    publish_event(conversation.id, event_message)
    return seq, event
