import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PROCESSING = "processing", "Processing"
        AWAITING_CLARIFICATION = "awaiting_clarification", "Awaiting Clarification"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or str(self.id)


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} @ {self.created_at:%Y-%m-%d %H:%M}"


class AgentEvent(models.Model):
    class EventType(models.TextChoices):
        TOKEN = "token", "Token"
        TOOL_START = "tool_start", "Tool Start"
        TOOL_END = "tool_end", "Tool End"
        PLAN = "plan", "Plan"
        TABLE = "table", "Table"
        CHART = "chart", "Chart"
        FILE_CREATED = "file_created", "File Created"
        FILE_UPDATED = "file_updated", "File Updated"
        ERROR = "error", "Error"
        CLARIFICATION = "clarification", "Clarification"
        PROVENANCE_ASK = "provenance_ask", "Provenance Ask"
        DONE = "done", "Done"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="events",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    payload = models.JSONField(default=dict)
    sequence_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence_number"],
                name="unique_conversation_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "sequence_number"]),
        ]

    def __str__(self):
        return f"{self.event_type} seq={self.sequence_number}"
