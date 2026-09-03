"""
Multi-agent team rosters for the AGENTS sidepane (REQ-23).

This is **not** the Django LLM-profile alias registry at /v1/teams/ (teams.json).
Rosters live in team_rosters.json (user config dir, else the packaged fixture)
and are listed at GET /v1/team-rosters/. Each team has a member roster used by
the chat dropdown (All members + per-member target).

Honesty: openai-agents handoff/as_tool fan-out is stubbed on the websocket
path until that runtime is wired. The UI still sends {team, target}.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.paths import (
    ensure_swarm_directories_exist,
    get_user_config_dir_for_swarm,
)
from swarm.permissions import HasValidTokenOrSession
from swarm.settings import ENABLE_API_AUTH

logger = logging.getLogger(__name__)

ROSTERS_API_PERMISSIONS = [HasValidTokenOrSession] if ENABLE_API_AUTH else [AllowAny]

PACKAGED_ROSTERS_PATH = Path(__file__).resolve().parents[1] / "data" / "team_rosters.json"

DEMO_TEAM_ROSTER = {
    "id": "demo-council",
    "object": "team_roster",
    "name": "Demo Council",
    "description": "Example multi-agent roster (not a /v1/teams LLM-profile alias).",
    "members": [
        {
            "id": "planner",
            "name": "Planner",
            "kind": "coordinator",
            "role": "coordinator",
        },
        {
            "id": "researcher",
            "name": "Researcher",
            "kind": "agent",
            "role": "researcher",
        },
        {
            "id": "writer",
            "name": "Writer",
            "kind": "agent",
            "role": "writer",
        },
    ],
}


def _user_rosters_path() -> Path:
    ensure_swarm_directories_exist()
    return get_user_config_dir_for_swarm() / "team_rosters.json"


def _normalize_member(raw: dict) -> dict | None:
    member_id = str(raw.get("id") or "").strip()
    if not member_id:
        return None
    kind = str(raw.get("kind") or raw.get("role") or "agent")
    role = str(raw.get("role") or raw.get("kind") or "member")
    return {
        "id": member_id,
        "name": str(raw.get("name") or member_id),
        "kind": kind,
        "role": role,
    }


def _normalize_team(raw: dict) -> dict | None:
    team_id = str(raw.get("id") or "").strip()
    if not team_id:
        return None
    members_raw = raw.get("members") if isinstance(raw.get("members"), list) else []
    members = []
    for item in members_raw:
        if isinstance(item, dict):
            member = _normalize_member(item)
            if member:
                members.append(member)
    return {
        "id": team_id,
        "object": "team_roster",
        "name": str(raw.get("name") or team_id),
        "description": str(raw.get("description") or ""),
        "members": members,
    }


def _teams_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, dict):
        raw_list = payload.get("data")
        if not isinstance(raw_list, list):
            raw_list = payload.get("teams")
    elif isinstance(payload, list):
        raw_list = payload
    else:
        raw_list = None
    if not isinstance(raw_list, list):
        return []
    teams = []
    for item in raw_list:
        if isinstance(item, dict):
            team = _normalize_team(item)
            if team:
                teams.append(team)
    return teams


def _read_json(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    return _teams_from_payload(json.loads(raw))


def load_team_rosters() -> list[dict]:
    """Load multi-agent rosters. Prefer user team_rosters.json, then packaged fixture.

    A present file that lists teams (including empty-member rosters) wins.
    Missing/unreadable files fall back to the packaged demo team so the
    sidepane has at least one team row.
    """
    user_path = _user_rosters_path()
    if user_path.exists():
        try:
            teams = _read_json(user_path)
            return teams
        except Exception:
            logger.exception("Failed to read %s; falling back to packaged fixture.", user_path)

    if PACKAGED_ROSTERS_PATH.exists():
        try:
            teams = _read_json(PACKAGED_ROSTERS_PATH)
            if teams:
                return teams
        except Exception:
            logger.exception("Failed to read packaged team_rosters.json; using inline demo.")

    return [deepcopy(DEMO_TEAM_ROSTER)]


def team_rosters_file(request):
    """GET /team_rosters.json — same payload as /v1/team-rosters/ for static fallback."""
    return JsonResponse({"object": "list", "data": load_team_rosters()})


class TeamRostersAPIView(APIView):
    """GET /v1/team-rosters/ — multi-agent rosters for the AGENTS sidepane."""

    permission_classes = ROSTERS_API_PERMISSIONS

    @extend_schema(
        operation_id="v1_team_rosters_list",
        summary="List multi-agent team rosters",
        description=(
            "List team rosters from team_rosters.json (not the /v1/teams "
            "LLM-profile alias registry). Each team has id, name, description, "
            "and members[{id,name,kind,role}]. Empty member lists are valid."
        ),
        responses={200: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        try:
            data = load_team_rosters()
            return Response({"object": "list", "data": data}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error listing team rosters.")
            return Response(
                {"error": "Failed to retrieve team rosters."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
