import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Integration",
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
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
                (
                    "type",
                    models.CharField(
                        choices=[("postgres", "PostgreSQL")],
                        max_length=32,
                    ),
                ),
                ("config", models.JSONField(default=dict)),
                ("schema_cache", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
