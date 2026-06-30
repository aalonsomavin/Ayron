import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("chat", "0003_clarification_status_and_event"),
        ("files", "0003_alter_file_conversation"),
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataAccess",
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
                ("tool_call_id", models.CharField(max_length=255)),
                (
                    "access_kind",
                    models.CharField(
                        choices=[
                            ("sql", "SQL"),
                            ("spreadsheet", "Spreadsheet"),
                            ("file", "File"),
                            ("api", "API"),
                        ],
                        max_length=16,
                    ),
                ),
                ("request", models.JSONField(default=dict)),
                ("response_summary", models.JSONField(default=dict)),
                ("executed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agent_event",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_accesses",
                        to="chat.agentevent",
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_accesses",
                        to="chat.conversation",
                    ),
                ),
                (
                    "file",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_accesses",
                        to="files.file",
                    ),
                ),
                (
                    "integration",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_accesses",
                        to="integrations.integration",
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_accesses",
                        to="chat.message",
                    ),
                ),
            ],
            options={
                "ordering": ["executed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dataaccess",
            index=models.Index(
                fields=["conversation", "tool_call_id"],
                name="provenance__convers_8a1b2c_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataaccess",
            constraint=models.UniqueConstraint(
                fields=("conversation", "tool_call_id"),
                name="unique_conversation_tool_call_data_access",
            ),
        ),
    ]
