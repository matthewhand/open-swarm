"""
JSON Teams API (ROADMAP 3.1).

REST endpoints over the same dynamic-team registry used by the server-rendered
/teams/ admin page (swarm.views.web_views.team_admin). Storage is the
file-backed JSON registry at <user config dir>/teams.json managed by
swarm.views.utils (load_dynamic_registry / register_dynamic_team /
deregister_dynamic_team).

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
from rest_framework import status
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
    GET  /v1/teams/  -> list registered dynamic teams
    POST /v1/teams/  -> register a new dynamic team
    """

    permission_classes = TEAMS_API_PERMISSIONS

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

            # Guard against collisions with statically discovered blueprints
            # (mirrors team_admin; best-effort, non-fatal on discovery errors).
            try:
                discovered = discover_blueprints(dj_settings.BLUEPRINT_DIRECTORY)
                if isinstance(discovered, dict) and slug in discovered:
                    return Response(
                        {"error": f"Name '{slug}' conflicts with an existing blueprint."},
                        status=status.HTTP_409_CONFLICT,
                    )
            except Exception:
                logger.debug("Blueprint collision check failed; continuing.", exc_info=True)

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
