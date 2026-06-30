import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_clarification_status_and_event"),
        ("files", "0003_alter_file_conversation"),
        ("provenance", "0002_rename_provenance__convers_8a1b2c_idx_provenance__convers_3882c0_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataClaim",
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
                ("claim_key", models.CharField(max_length=255)),
                (
                    "surface",
                    models.CharField(
                        choices=[
                            ("dashboard_kpi", "Dashboard KPI"),
                            ("chat_chart", "Chat chart"),
                            ("chat_table", "Chat table"),
                        ],
                        max_length=32,
                    ),
                ),
                ("label", models.CharField(max_length=255)),
                ("definition", models.JSONField(default=dict)),
                ("artifact_version", models.PositiveIntegerField(default=1)),
                (
                    "artifact_file",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_claims",
                        to="files.file",
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_claims",
                        to="chat.conversation",
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_claims",
                        to="chat.message",
                    ),
                ),
            ],
            options={
                "ordering": ["claim_key"],
            },
        ),
        migrations.CreateModel(
            name="ProvenanceLink",
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
                ("transformation", models.CharField(blank=True, max_length=512)),
                ("ordinal", models.PositiveIntegerField(default=0)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provenance_links",
                        to="provenance.dataclaim",
                    ),
                ),
                (
                    "data_access",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provenance_links",
                        to="provenance.dataaccess",
                    ),
                ),
            ],
            options={
                "ordering": ["ordinal"],
            },
        ),
        migrations.AddIndex(
            model_name="dataclaim",
            index=models.Index(
                fields=["conversation", "claim_key"],
                name="provenance__convers_claim_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataclaim",
            constraint=models.UniqueConstraint(
                condition=models.Q(("artifact_file__isnull", False)),
                fields=("artifact_file", "claim_key"),
                name="unique_artifact_file_claim_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataclaim",
            constraint=models.UniqueConstraint(
                condition=models.Q(("artifact_file__isnull", True)),
                fields=("conversation", "message", "claim_key"),
                name="unique_inline_message_claim_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="provenancelink",
            constraint=models.UniqueConstraint(
                fields=("claim", "ordinal"),
                name="unique_claim_provenance_ordinal",
            ),
        ),
    ]
