import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("files", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedDashboard",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("pinned", models.BooleanField(default=False)),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
                (
                    "file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_by",
                        to="files.file",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_dashboards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-pinned", "-saved_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="saveddashboard",
            constraint=models.UniqueConstraint(
                fields=("user", "file"),
                name="unique_saved_dashboard_per_user",
            ),
        ),
    ]
