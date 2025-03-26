"""
Views related to Chat Messages.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from swarm.models import ChatMessage
from swarm.serializers import ChatMessageSerializer

class ChatMessageViewSet(ModelViewSet):
    """API viewset for managing chat messages."""
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ChatMessage.objects.all().order_by('-timestamp') # Order by timestamp descending
    serializer_class = ChatMessageSerializer

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
