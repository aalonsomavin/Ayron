from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0004_agentevent_provenance_ask"),
    ]

    operations = [
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
                    ("provenance_ask", "Provenance Ask"),
                    ("provenance_diagram", "Provenance Diagram"),
                    ("done", "Done"),
                ],
                max_length=20,
            ),
        ),
    ]
