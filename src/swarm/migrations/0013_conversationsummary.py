# REQ-37: nested conversation compact / summaries. Local Django sqlite only.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("swarm", "0012_herdragent"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversationSummary",
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
                ("span", models.JSONField(default=dict)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summaries",
                        to="swarm.chatconversation",
                    ),
                ),
                (
                    "parent_summary",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_summaries",
                        to="swarm.conversationsummary",
                    ),
                ),
            ],
            options={
                "verbose_name": "Conversation Summary",
                "verbose_name_plural": "Conversation Summaries",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
