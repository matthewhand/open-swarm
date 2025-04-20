from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
import os
from swarm.auth import EnvOrTokenAuthentication
from blueprints.chc.models import AgentInstruction
from blueprints.chc.serializers import AgentInstructionSerializer

class AgentInstructionViewSet(ModelViewSet):
    authentication_classes = [EnvOrTokenAuthentication]
    permission_classes = [AllowAny]
    queryset = AgentInstruction.objects.all()
    serializer_class = AgentInstructionSerializer

    def get_permissions(self):
        if os.getenv("ENABLE_API_AUTH", "false").lower() in ("true", "1", "t"):
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_authentication(self, request):
        super().perform_authentication(request)
        if not request.user or not request.user.is_authenticated:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed("Invalid token.")

__all__ = ["AgentInstructionViewSet"]
