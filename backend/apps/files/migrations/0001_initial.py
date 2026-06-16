import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.files.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("chat", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="File",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("original_name", models.CharField(max_length=255)),
                (
                    "mime_type",
                    models.CharField(
                        default="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        max_length=128,
                    ),
                ),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("file", models.FileField(upload_to=apps.files.models.conversation_file_path)),
                ("content_json", models.JSONField(default=dict)),
                ("preview_html", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to="chat.conversation",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
