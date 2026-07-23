"""
Views related to Chat Messages.
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from swarm.auth import api_permission_classes
from swarm.models import ChatMessage
from swarm.serializers import ChatMessageSerializer


class ChatMessageViewSet(ModelViewSet):
    """API viewset for managing chat messages.

    Chat is web-session oriented. When ``ENABLE_API_AUTH`` is on, list/retrieve
    are scoped to the authenticated session user's conversations; token-only
    (AnonymousUser + static token) and anonymous clients get an empty queryset.
    """

    queryset = ChatMessage.objects.all().order_by('-timestamp')
    serializer_class = ChatMessageSerializer

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get_queryset(self):
        qs = ChatMessage.objects.all().order_by('-timestamp')
        if not getattr(settings, 'ENABLE_API_AUTH', False):
            return qs
        user = getattr(self.request, 'user', None)
        if user is not None and user.is_authenticated:
            # Only messages in conversations owned by this session user.
            # Null-student (legacy) rows are not shared when auth is on.
            return qs.filter(conversation__student=user)
        # Token-only or anonymous with auth on: chat is session-oriented.
        return qs.none()

    def perform_create(self, serializer):
        """Create a message; stamp conversation.student for session users.

        When auth is on and the requester is a session user, ensure the target
        conversation is owned by them (set student if still null; refuse if it
        belongs to someone else). Token-only creates are left alone — the
        queryset already hides those rows from list/retrieve.
        """
        message = serializer.save()
        if not getattr(settings, 'ENABLE_API_AUTH', False):
            return
        user = getattr(self.request, 'user', None)
        if user is None or not user.is_authenticated:
            return
        conversation = message.conversation
        if conversation.student_id is None:
            conversation.student = user
            conversation.save(update_fields=['student'])
        elif conversation.student_id != user.id:
            # Should not happen if clients only post to own conversations;
            # delete the just-created row and surface a permission error.
            message.delete()
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Cannot add messages to another user's conversation."
            )

    @extend_schema(summary="List all chat messages")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Retrieve a chat message by its unique id")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Create a new chat message")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Update an existing chat message")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Partially update a chat message")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Delete a chat message by its unique id")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
