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

__all__ = [
    "ChatConversation",
    "ChatMessage",
]

# Alias the module to prevent conflicting model registrations.
import sys

sys.modules["swarm.models"] = sys.modules[__name__]
sys.modules["src.swarm.models"] = sys.modules["swarm.models"]
