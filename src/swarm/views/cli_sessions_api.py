"""REQ-104 — list / select CLI-provider sessions.

GET  /v1/cli-sessions/?agent=&cli=
POST /v1/cli-sessions/select/   {agent, cli, session_id | start_new}
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

logger = logging.getLogger(__name__)


def _user_key(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        try:
            return user_key_for(user)
        except Exception:
            logger.exception("Could not resolve user_key")
    return "u0"


def _resolve_cli(agent_id: str, cli: str | None) -> str:
    raw = (cli or "").strip()
    if raw:
        return normalize_agent_id(raw)
    mapped = cli_from_rail_id(agent_id)
    if mapped:
        return mapped
    if agent_id == "cli_agent":
        return "grok"
    return normalize_agent_id(agent_id)


def _swarm_config() -> dict:
    try:
        from swarm.core.llm_task_routing import load_swarm_config

        cfg = load_swarm_config()
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


class CliSessionListAPIView(APIView):
    """GET /v1/cli-sessions/?agent=&cli= — provider list + swarm recents."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_cli_sessions_list",
        summary="List CLI-provider sessions for one rail agent",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        from swarm.core.cli_session_select import list_cli_sessions

        agent = normalize_agent_id(request.query_params.get("agent") or "cli_agent")
        cli = _resolve_cli(agent, request.query_params.get("cli"))
        payload = list_cli_sessions(
            _user_key(request),
            agent,
            cli,
            config=_swarm_config(),
        )
        return Response(payload, status=status.HTTP_200_OK)


class CliSessionSelectAPIView(APIView):
    """POST /v1/cli-sessions/select/ — design A bind (new Django conversation)."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_cli_sessions_select",
        summary="Bind a new conversation to a CLI session (or start fresh)",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *_args, **_kwargs):
        from swarm.core.cli_session_select import select_cli_session

        body = request.data if isinstance(request.data, dict) else {}
        agent = normalize_agent_id(str(body.get("agent") or body.get("agent_id") or "cli_agent"))
        cli = _resolve_cli(agent, body.get("cli") if isinstance(body.get("cli"), str) else None)
        start_new = bool(body.get("start_new"))
        raw_sid = body.get("session_id")
        session_id = raw_sid.strip() if isinstance(raw_sid, str) else None
        if not start_new and not session_id:
            return Response(
                {"error": "session_id is required unless start_new is true"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from_cid = ""
        raw_from = body.get("from_conversation_id") or body.get("conversation_id")
        if isinstance(raw_from, str):
            from_cid = raw_from.strip()
        title = str(body.get("title") or "")[:200]
        snippet = str(body.get("snippet") or "")[:240]
        user = getattr(request, "user", None)
        try:
            payload = select_cli_session(
                _user_key(request),
                agent,
                cli,
                session_id=session_id,
                start_new=start_new,
                from_conversation_id=from_cid,
                user=user,
                title=title,
                snippet=snippet,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError:
            logger.exception("Failed to persist CLI session select for %s/%s", agent, cli)
            return Response(
                {"error": "Could not switch session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload, status=status.HTTP_200_OK)
