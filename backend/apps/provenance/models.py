import uuid

from django.db import models


class DataAccess(models.Model):
    class AccessKind(models.TextChoices):
        SQL = "sql", "SQL"
        SPREADSHEET = "spreadsheet", "Spreadsheet"
        FILE = "file", "File"
        API = "api", "API"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.CASCADE,
        related_name="data_accesses",
    )
    message = models.ForeignKey(
        "chat.Message",
        on_delete=models.SET_NULL,
        related_name="data_accesses",
        null=True,
        blank=True,
    )
    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.SET_NULL,
        related_name="data_accesses",
        null=True,
        blank=True,
    )
    file = models.ForeignKey(
        "files.File",
        on_delete=models.SET_NULL,
        related_name="data_accesses",
        null=True,
        blank=True,
    )
    tool_call_id = models.CharField(max_length=255)
    agent_event = models.ForeignKey(
        "chat.AgentEvent",
        on_delete=models.SET_NULL,
        related_name="data_accesses",
        null=True,
        blank=True,
    )
    access_kind = models.CharField(max_length=16, choices=AccessKind.choices)
    request = models.JSONField(default=dict)
    response_summary = models.JSONField(default=dict)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["executed_at"]
        indexes = [
            models.Index(fields=["conversation", "tool_call_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "tool_call_id"],
                name="unique_conversation_tool_call_data_access",
            ),
        ]

    def __str__(self):
        return f"{self.access_kind} {self.tool_call_id}"
