import uuid

from django.conf import settings
from django.db import models

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HTML_MIME = "text/html"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MIME_EXTENSIONS = {
    DOCX_MIME: ".docx",
    HTML_MIME: ".html",
    XLSX_MIME: ".xlsx",
}


def conversation_file_path(instance, filename):
    conversation_id = instance.conversation_id or "orphan"
    ext = MIME_EXTENSIONS.get(instance.mime_type, ".bin")
    return f"conversations/{conversation_id}/{instance.id}{ext}"


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="files",
    )
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.SET_NULL,
        related_name="files",
        null=True,
        blank=True,
    )
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128, default=DOCX_MIME)
    size_bytes = models.PositiveIntegerField(default=0)
    file = models.FileField(upload_to=conversation_file_path)
    content_json = models.JSONField(default=dict)
    preview_html = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.original_name

    @property
    def format_key(self) -> str:
        format_key = self.content_json.get("format")
        if format_key:
            return format_key
        if self.mime_type == HTML_MIME:
            return "html"
        if self.mime_type == XLSX_MIME:
            return "xlsx"
        return "docx"


class SavedDashboard(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_dashboards",
    )
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name="saved_by",
    )
    pinned = models.BooleanField(default=False)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "file"],
                name="unique_saved_dashboard_per_user",
            )
        ]
        ordering = ["-pinned", "-saved_at"]

    def __str__(self):
        return f"{self.user_id} · {self.file_id}"
