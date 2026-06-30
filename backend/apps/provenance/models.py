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
    source_ref = models.CharField(max_length=32, blank=True, default="")
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
            models.Index(fields=["conversation", "source_ref"], name="provenance__convers_source_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "tool_call_id"],
                name="unique_conversation_tool_call_data_access",
            ),
            models.UniqueConstraint(
                fields=["conversation", "source_ref"],
                condition=models.Q(source_ref__gt=""),
                name="unique_conversation_source_ref",
            ),
        ]

    def __str__(self):
        return f"{self.access_kind} {self.tool_call_id}"


class DataClaim(models.Model):
    class Surface(models.TextChoices):
        DASHBOARD_KPI = "dashboard_kpi", "Dashboard KPI"
        CHAT_CHART = "chat_chart", "Chat chart"
        CHAT_TABLE = "chat_table", "Chat table"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_key = models.CharField(max_length=255)
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.CASCADE,
        related_name="data_claims",
    )
    message = models.ForeignKey(
        "chat.Message",
        on_delete=models.SET_NULL,
        related_name="data_claims",
        null=True,
        blank=True,
    )
    artifact_file = models.ForeignKey(
        "files.File",
        on_delete=models.CASCADE,
        related_name="data_claims",
        null=True,
        blank=True,
    )
    surface = models.CharField(max_length=32, choices=Surface.choices)
    label = models.CharField(max_length=255)
    definition = models.JSONField(default=dict)
    artifact_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["claim_key"]
        indexes = [
            models.Index(fields=["conversation", "claim_key"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["artifact_file", "claim_key"],
                condition=models.Q(artifact_file__isnull=False),
                name="unique_artifact_file_claim_key",
            ),
            models.UniqueConstraint(
                fields=["conversation", "message", "claim_key"],
                condition=models.Q(artifact_file__isnull=True),
                name="unique_inline_message_claim_key",
            ),
        ]

    def __str__(self):
        return f"{self.claim_key} ({self.surface})"


class ProvenanceLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(
        DataClaim,
        on_delete=models.CASCADE,
        related_name="provenance_links",
    )
    data_access = models.ForeignKey(
        DataAccess,
        on_delete=models.CASCADE,
        related_name="provenance_links",
    )
    transformation = models.CharField(max_length=512, blank=True)
    ordinal = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordinal"]
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "ordinal"],
                name="unique_claim_provenance_ordinal",
            ),
        ]

    def __str__(self):
        return f"{self.claim.claim_key} → {self.data_access.tool_call_id}"
