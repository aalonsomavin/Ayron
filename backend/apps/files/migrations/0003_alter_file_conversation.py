import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
        ("files", "0002_saveddashboard"),
    ]

    operations = [
        migrations.AlterField(
            model_name="file",
            name="conversation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="files",
                to="chat.conversation",
            ),
        ),
    ]
