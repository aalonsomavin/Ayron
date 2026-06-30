from django.db import migrations, models


def backfill_source_refs(apps, schema_editor):
    DataAccess = apps.get_model("provenance", "DataAccess")
    conversation_ids = (
        DataAccess.objects.filter(access_kind="sql")
        .values_list("conversation_id", flat=True)
        .distinct()
    )
    for conversation_id in conversation_ids:
        rows = list(
            DataAccess.objects.filter(
                conversation_id=conversation_id,
                access_kind="sql",
            ).order_by("executed_at", "id")
        )
        for index, row in enumerate(rows, start=1):
            if not row.source_ref:
                row.source_ref = f"sql_{index}"
                row.save(update_fields=["source_ref"])


def clear_source_refs(apps, schema_editor):
    DataAccess = apps.get_model("provenance", "DataAccess")
    DataAccess.objects.update(source_ref="")


class Migration(migrations.Migration):

    dependencies = [
        ("provenance", "0004_rename_provenance__convers_claim_idx_provenance__convers_4b984f_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataaccess",
            name="source_ref",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.RunPython(backfill_source_refs, clear_source_refs),
        migrations.AddIndex(
            model_name="dataaccess",
            index=models.Index(
                fields=["conversation", "source_ref"],
                name="provenance__convers_source_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataaccess",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_ref__gt", "")),
                fields=("conversation", "source_ref"),
                name="unique_conversation_source_ref",
            ),
        ),
    ]
