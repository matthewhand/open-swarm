import uuid

from django.db import models


class ChatConversation(models.Model):
    """Represents a single chat session."""
    conversation_id = models.CharField(max_length=255, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    student = models.ForeignKey("auth.User", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        app_label = "swarm"
        verbose_name = "Chat Conversation"
        verbose_name_plural = "Chat Conversations"

    def __str__(self):
        return f"ChatConversation({self.conversation_id})"

    @property
    def messages(self):
        return self.chat_messages.all()

class ChatMessage(models.Model):
    """Stores individual chat messages within a conversation."""
    conversation = models.ForeignKey(ChatConversation, related_name="chat_messages", on_delete=models.CASCADE)
    sender = models.CharField(max_length=50)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    tool_call_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return self.content[:50]


class ChatAttachment(models.Model):
    """Uploaded file attached to the next chat send (REQ-38).

    Bytes live under ``SWARM_USER_DATA_DIR/attachments`` (or
    ``SWARM_ATTACHMENTS_DIR``), keyed by owner + id. SQLite holds metadata
    only — no Neon, no secrets in fixtures.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="chat_attachments",
    )
    conversation_id = models.CharField(max_length=255, blank=True, default="")
    original_name = models.CharField(max_length=512)
    content_type = models.CharField(max_length=255, blank=True, default="")
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "swarm"
        verbose_name = "Chat Attachment"
        verbose_name_plural = "Chat Attachments"
        ordering = ["created_at"]

    def __str__(self):
        return f"ChatAttachment({self.original_name})"


# Marketplace models live in a submodule; import them here so they are always
# registered with Django when the app loads. Otherwise a stray import of
# swarm.models.core_models at test collection registers them without
# migrations and breaks test-database serialization.
from swarm.models.core_models import (  # noqa: E402
    Blueprint,
    MarketplaceIndex,
    MCPConfig,
)

__all__ = [
    "ChatConversation",
    "ChatMessage",
    "ChatAttachment",
    "Blueprint",
    "MCPConfig",
    "MarketplaceIndex",
]

