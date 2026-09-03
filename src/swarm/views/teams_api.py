"""
JSON Teams API (ROADMAP 3.1).

REST endpoints over the same dynamic-team registry used by the server-rendered
/teams/ admin page (swarm.views.web_views.team_admin). Storage is the
file-backed JSON registry at <user config dir>/teams.json managed by
swarm.views.utils (load_dynamic_registry / register_dynamic_team /
deregister_dynamic_team).

Honesty: a "team" here is a named **LLM-profile alias** (id + description +
llm_profile), not a multi-agent Team. REQ-11 Team = API/CLI/remote members that
see and talk via openai-agents handoff/as_tool (see ``/v1/remotes/`` +
``/v1/agent-team/``). Prefer **Profiles** for this alias registry. Entries
appear in /v1/models and can be selected as OpenAI-compatible model ids.

Endpoints:
    GET    /v1/teams/          -> {"object": "list", "data": [team, ...]}
    POST   /v1/teams/          -> 201 + team
    DELETE /v1/teams/<id>/     -> 204 (404 if unknown)

Permissions follow the project's API auth pattern: when API auth is enabled
(API_AUTH_TOKEN/SWARM_API_KEY configured), HasValidTokenOrSession is required;
otherwise AllowAny, matching /v1/blueprints/ behaviour in unauthenticated
deployments.
"""

import logging

from django.conf import settings as dj_settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.permissions import HasValidTokenOrSession
from swarm.settings import ENABLE_API_AUTH
from swarm.views.utils import (
    deregister_dynamic_team,
    load_dynamic_registry,
    register_dynamic_team,
)

logger = logging.getLogger(__name__)

# Mirrors REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES in swarm/settings.py.
TEAMS_API_PERMISSIONS = [HasValidTokenOrSession] if ENABLE_API_AUTH else [AllowAny]


def _slugify_team_name(name: str) -> str:
    """Slugify a team name the same way the /teams/ admin form does."""
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def _serialize_team(entry: dict) -> dict:
    return {
        "id": entry.get("id"),
        "object": "team",
        "description": entry.get("description") or "",
        "llm_profile": entry.get("llm_profile") or "default",
    }


class TeamsAPIView(APIView):
    """
    GET  /v1/teams/  -> list registered dynamic teams (LLM-profile aliases)
    POST /v1/teams/  -> register a new dynamic team
    """

    permission_classes = TEAMS_API_PERMISSIONS

    @extend_schema(
        operation_id="v1_teams_list",
        summary="List dynamic teams (LLM-profile aliases)",
        description=(
            "List saved dynamic teams from teams.json. Prefer calling these "
            "**Profiles**: each entry is an OpenAI-compatible model id alias "
            "over an `llm_profile` (id, description, llm_profile). This is not "
            "a multi-agent Team. REQ-11 Team (API/CLI/remote handoff members) "
            "is GET /v1/agent-team/."
        ),
        responses={200: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        try:
            teams = list(load_dynamic_registry().values())
            data = [_serialize_team(t) for t in teams]
            return Response({"object": "list", "data": data}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error retrieving teams list.")
            return Response(
                {"error": "Failed to retrieve teams list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="v1_teams_create",
        summary="Register a dynamic team (LLM-profile alias)",
        description=(
            "Register a named Profile alias (saved `llm_profile` on /v1/teams/). "
            "`name` is **required**; it is slugified into the id. "
            "This is not a multi-agent Team — place remotes via /v1/agent-team/."
        ),
        request=inline_serializer(
            name="TeamCreateRequest",
            fields={
                "name": serializers.CharField(
                    help_text="Team name (required). Slugified into the team id."
                ),
                "description": serializers.CharField(
                    required=False, allow_blank=True, help_text="Optional human description."
                ),
                "llm_profile": serializers.CharField(
                    required=False,
                    allow_blank=True,
                    help_text="LLM profile name to use (defaults to 'default').",
                ),
            },
        ),
        examples=[
            OpenApiExample(
                "Minimal",
                value={"name": "research-squad", "llm_profile": "default"},
                request_only=True,
            )
        ],
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request, *_args, **_kwargs):
        try:
            body = request.data or {}
            name = (body.get("name") or body.get("id") or "").strip()
            description = (body.get("description") or "").strip() or None
            llm_profile = (body.get("llm_profile") or "").strip() or None

            if not name:
                return Response(
                    {"error": "Team name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            slug = _slugify_team_name(name)
            if not slug:
                return Response(
                    {"error": "Team name must contain letters or numbers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(slug) > 64:
                return Response(
                    {"error": "Team name too long (max 64)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Uniqueness vs the dynamic registry.
            if slug in load_dynamic_registry():
                return Response(
                    {"error": f"Team '{slug}' already exists."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Guard against collisions with statically discovered blueprints.
            # Fail closed: discovery errors must not allow shadowing a static blueprint.
            try:
                discovered = discover_blueprints(dj_settings.BLUEPRINT_DIRECTORY)
            except Exception:
                logger.exception("Blueprint collision check failed; refusing team create.")
                return Response(
                    {"error": "Unable to verify team name against existing blueprints."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if isinstance(discovered, dict) and slug in discovered:
                return Response(
                    {"error": f"Name '{slug}' conflicts with an existing blueprint."},
                    status=status.HTTP_409_CONFLICT,
                )

            register_dynamic_team(slug, description=description, llm_profile=llm_profile)
            team = load_dynamic_registry().get(slug) or {
                "id": slug,
                "description": description,
                "llm_profile": llm_profile,
            }
            return Response(_serialize_team(team), status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Error creating team.")
            return Response(
                {"error": "Failed to create team."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TeamDetailAPIView(APIView):
    """
    DELETE /v1/teams/<team_id>/ -> deregister a dynamic team
    """

    permission_classes = TEAMS_API_PERMISSIONS

    def delete(self, request, team_id: str, *_args, **_kwargs):
        try:
            if deregister_dynamic_team(team_id):
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error deleting team '%s'.", team_id)
            return Response(
                {"error": "Failed to delete team."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
