"""REQ-114 — inspect / terminate a swarm-spawned CLI subprocess.

GET  /v1/cli-agents/runs/?agent=
POST /v1/cli-agents/runs/terminate/   {agent, conversation_id?}

v1 is CLI only. API / remote / team agents are rejected (400). Idle CLI
returns ``not_running`` — the rail disables Terminate with “Nothing running”.
Terminate kills the registered process group (SIGTERM then SIGKILL) and does
not delete the agent, wipe the session id, or clear the transcript.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core.chat_store import normalize_agent_id, user_key_for
from swarm.core.cli_catalog import cli_from_rail_id
from swarm.core.cli_run_registry import is_cli_run_running, list_cli_runs, terminate_cli_runs

logger = logging.getLogger(__name__)


def _user_key(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        try:
            return user_key_for(user)
        except Exception:
            logger.exception("Could not resolve user_key")
    return "u0"


def _cli_terminate_error(agent_id: str) -> str | None:
    """None if this rail id may be terminated; else a 400 message."""
    raw = (agent_id or "").strip()
    lowered = raw.lower()
    if lowered == "api_agent":
        return "Terminate is only available for CLI agents"
    if lowered.startswith("team:") or lowered.startswith("remote:"):
        return "Terminate is only available for CLI agents"
    if lowered == "cli_agent" or cli_from_rail_id(raw):
        return None
    # Unknown seat: do not pretend it is a CLI run we can stop.
    return "Terminate is only available for CLI agents"


def _agent_from(request, body: dict | None = None) -> str:
    if body:
        raw = body.get("agent") or body.get("agent_id")
        if isinstance(raw, str) and raw.strip():
            return normalize_agent_id(raw)
    query = request.query_params.get("agent") or request.query_params.get("agent_id")
    return normalize_agent_id(query or "cli_agent")


def _conversation_from(body: dict | None, request=None) -> str:
    if body:
        raw = body.get("conversation_id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    if request is not None:
        raw = request.query_params.get("conversation_id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


class CliRunStatusAPIView(APIView):
    """GET /v1/cli-agents/runs/?agent= — is a CLI subprocess running?"""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_cli_runs_status",
        summary="Whether a tracked CLI subprocess is running for a rail agent",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        agent = _agent_from(request)
        err = _cli_terminate_error(agent)
        if err:
            return Response({"error": err, "running": False}, status=status.HTTP_400_BAD_REQUEST)
        user_key = _user_key(request)
        conversation_id = _conversation_from(None, request) or None
        runs = list_cli_runs(user_key, agent, conversation_id=conversation_id)
        return Response(
            {
                "object": "cli_run_status",
                "agent": agent,
                "running": bool(runs),
                "count": len(runs),
            },
            status=status.HTTP_200_OK,
        )


class CliRunTerminateAPIView(APIView):
    """POST /v1/cli-agents/runs/terminate/ — SIGTERM then SIGKILL the group."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_cli_runs_terminate",
        summary="Terminate the swarm-spawned CLI process group for one rail agent",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        agent = _agent_from(request, body)
        err = _cli_terminate_error(agent)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        user_key = _user_key(request)
        conversation_id = _conversation_from(body) or None
        state = terminate_cli_runs(user_key, agent, conversation_id=conversation_id)
        return Response(
            {
                "object": "cli_run_terminate",
                "agent": agent,
                "status": state,
                "running": is_cli_run_running(user_key, agent, conversation_id=conversation_id),
            },
            status=status.HTTP_200_OK,
        )
