"""REQ-105: agent-scoped session metadata on ChatConversation."""

from django.db import migrations, models


def _infer_agent_id(conversation_id: str) -> str:
    text = (conversation_id or "").strip()
    if text.startswith("agt-"):
        parts = text.split("-", 2)
        return parts[2][:128] if len(parts) == 3 else ""
    if text.startswith("task-"):
        rest = text[5:]
        if rest and rest[0].isdigit():
            parts = rest.split("-", 1)
            return parts[1].rsplit("-", 1)[0][:128] if len(parts) == 2 else ""
        return rest.rsplit("-", 1)[0][:128]
    return ""


def backfill_session_metadata(apps, schema_editor):
    ChatConversation = apps.get_model("swarm", "ChatConversation")
    ChatMessage = apps.get_model("swarm", "ChatMessage")
    for row in ChatConversation.objects.all().iterator():
        changed = False
        if not row.agent_id:
            inferred = _infer_agent_id(row.conversation_id)
            if inferred:
                row.agent_id = inferred
                changed = True
        if not row.title:
            row.title = "Session 1"
            changed = True
        if not row.snippet:
            last = (
                ChatMessage.objects.filter(conversation_id=row.conversation_id)
                .exclude(sender="status")
                .order_by("-timestamp")
                .first()
            )
            if last and last.content:
                text = " ".join(str(last.content).split())
                row.snippet = text[:254] + "…" if len(text) > 255 else text
                changed = True
        if changed:
            row.save()


class Migration(migrations.Migration):

    dependencies = [
        ("swarm", "0015_userpreference"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatconversation",
            name="agent_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="cli_session_id",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="labels",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="snippet",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="chatconversation",
            index=models.Index(
                fields=["student", "agent_id", "-updated_at"],
                name="swarm_chat_agent_upd",
            ),
        ),
        migrations.RunPython(backfill_session_metadata, migrations.RunPython.noop),
    ]
