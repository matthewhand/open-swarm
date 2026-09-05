"""REQ-121: per-conversation cull / start-from-here metadata."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("swarm", "0016_chatconversation_agent_session"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatconversation",
            name="context_meta",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
