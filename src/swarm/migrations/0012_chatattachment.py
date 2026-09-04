# REQ-38: sqlite metadata for composer file attachments.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("swarm", "0011_blueprint_marketplaceindex_mcpconfig"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatAttachment",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("conversation_id", models.CharField(blank=True, default="", max_length=255)),
                ("original_name", models.CharField(max_length=512)),
                ("content_type", models.CharField(blank=True, default="", max_length=255)),
                ("size", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Chat Attachment",
                "verbose_name_plural": "Chat Attachments",
                "ordering": ["created_at"],
            },
        ),
    ]
