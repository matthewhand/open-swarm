"""Per-agent settings API (REQ-65).

GET/PATCH ``/v1/agents/<id>/settings/`` — agent-scoped only. Not global
Settings (Remotes / Retention / Hostname).
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.agent_settings import get_settings, update_settings
from swarm.core.chat_store import normalize_agent_id
from swarm.core.session_policy import allocate_task_session, list_active_task_sessions
from swarm.permissions import HasValidTokenOrSession
from swarm.settings import ENABLE_API_AUTH

logger = logging.getLogger(__name__)

SETTINGS_API_PERMISSIONS = [HasValidTokenOrSession] if ENABLE_API_AUTH else [AllowAny]


def _error(message: str, code: int) -> Response:
    return Response({"error": message}, status=code)


def _payload(agent_id: str, settings: dict, request) -> dict:
    user = getattr(request, "user", None)
    user_key = ""
    try:
        from swarm.core.chat_store import user_key_for

        if user is not None and getattr(user, "is_authenticated", False):
            user_key = user_key_for(user)
    except Exception:
        user_key = ""
    sessions = list_active_task_sessions(user_key, agent_id) if user_key else []
    return {
        "object": "agent_settings",
        "agent_id": agent_id,
        "new_chat_per_task": bool(settings.get("new_chat_per_task")),
        "cli_session_id": settings.get("cli_session_id"),
        "remote_session_id": settings.get("remote_session_id"),
        "active_sessions": sessions,
    }


class AgentSettingsAPIView(APIView):
    """GET/PATCH /v1/agents/<agent_id>/settings/"""

    permission_classes = SETTINGS_API_PERMISSIONS

    @extend_schema(
        operation_id="v1_agent_settings_get",
        summary="Get agent-scoped settings (new chat per task)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, agent_id: str, *_args, **_kwargs):
        agent = normalize_agent_id(agent_id)
        return Response(_payload(agent, get_settings(agent), request), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="v1_agent_settings_patch",
        summary="Update agent-scoped settings (new chat per task)",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def patch(self, request, agent_id: str, *_args, **_kwargs):
        agent = normalize_agent_id(agent_id)
        body = request.data if isinstance(request.data, dict) else {}
        try:
            settings = update_settings(agent, body)
        except ValueError as exc:
            return _error(str(exc), status.HTTP_400_BAD_REQUEST)
        except OSError:
            logger.exception("Failed to persist agent settings for %s", agent)
            return _error("Could not save agent settings.", status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(_payload(agent, settings, request), status=status.HTTP_200_OK)


class AgentTaskSessionAPIView(APIView):
    """POST /v1/agents/<agent_id>/sessions/ — swarm owns session create."""

    permission_classes = SETTINGS_API_PERMISSIONS

    @extend_schema(
        operation_id="v1_agent_task_session_create",
        summary="Allocate a chat session for one task (honours new_chat_per_task)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, agent_id: str, *_args, **_kwargs):
        agent = normalize_agent_id(agent_id)
        body = request.data if isinstance(request.data, dict) else {}
        task_id = str(body.get("task_id") or "").strip() or None
        session = allocate_task_session(request.user, agent, task_id=task_id)
        return Response(
            {
                "object": "agent_task_session",
                "agent_id": session.agent_id,
                "conversation_id": session.conversation_id,
                "new_chat_per_task": session.new_chat_per_task,
                "empty": session.empty,
                "resume_external": session.resume_external,
                "task_id": session.task_id,
            },
            status=status.HTTP_200_OK,
        )
