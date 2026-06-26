from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_alter_agentevent_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("processing", "Processing"),
                    ("awaiting_clarification", "Awaiting Clarification"),
                    ("failed", "Failed"),
                ],
                default="active",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="agentevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("token", "Token"),
                    ("tool_start", "Tool Start"),
                    ("tool_end", "Tool End"),
                    ("plan", "Plan"),
                    ("table", "Table"),
                    ("chart", "Chart"),
                    ("file_created", "File Created"),
                    ("file_updated", "File Updated"),
                    ("error", "Error"),
                    ("clarification", "Clarification"),
                    ("done", "Done"),
                ],
                max_length=20,
            ),
        ),
    ]
