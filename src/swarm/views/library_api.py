"""
JSON Blueprint Library API (SPA parity).

REST endpoints over the same file-backed library used by the server-rendered
/blueprint-library/ pages (swarm.views.blueprint_library_views). Storage is
<user config dir>/blueprint_library.json with the shape
{"installed": [name, ...], "custom": [...]}; this API manages the "installed"
list (custom blueprints already have their own API at /v1/blueprints/custom/).

Note: like the Django views it mirrors, the library is a single file per OS
user / server deployment, not per Django user.

Endpoints:
    GET    /v1/library/         -> {"object": "list", "data": [entry, ...]}
    POST   /v1/library/ {name}  -> 201 + entry (200 if already in library)
    DELETE /v1/library/<name>/  -> 204 (404 if not in library)

Permissions follow the project's API auth pattern (same as /v1/teams/): when
API auth is enabled (API_AUTH_TOKEN/SWARM_API_KEY configured),
HasValidTokenOrSession is required; otherwise AllowAny.
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.permissions import HasValidTokenOrSession
from swarm.settings import BLUEPRINT_DIRECTORY, ENABLE_API_AUTH
from swarm.views.blueprint_library_views import (
    BLUEPRINT_METADATA,
    get_user_blueprint_library,
    save_user_blueprint_library,
)

logger = logging.getLogger(__name__)

# Mirrors REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES in swarm/settings.py.
LIBRARY_API_PERMISSIONS = [HasValidTokenOrSession] if ENABLE_API_AUTH else [AllowAny]


def _serialize_entry(blueprint_name: str) -> dict:
    """Serialize a library entry, reusing the Django pages' metadata fallback."""
    metadata = BLUEPRINT_METADATA.get(blueprint_name, {})
    return {
        "id": blueprint_name,
        "object": "library.blueprint",
        "name": metadata.get("name", blueprint_name.replace("_", " ").title()),
        "description": metadata.get("description", f"Blueprint for {blueprint_name}"),
    }


class LibraryAPIView(APIView):
    """
    GET  /v1/library/  -> list blueprints in the user's library
    POST /v1/library/  -> add a blueprint to the library
    """

    permission_classes = LIBRARY_API_PERMISSIONS

    def get(self, request, *_args, **_kwargs):
        try:
            library = get_user_blueprint_library()
            installed = library.get("installed", [])
            data = [_serialize_entry(name) for name in installed]
            return Response({"object": "list", "data": data}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error retrieving blueprint library.")
            return Response(
                {"error": "Failed to retrieve blueprint library."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, *_args, **_kwargs):
        try:
            body = request.data or {}
            name = (body.get("name") or body.get("id") or "").strip()
            if not name:
                return Response(
                    {"error": "Blueprint name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify the blueprint exists, mirroring add_blueprint_to_library.
            discovered = discover_blueprints(BLUEPRINT_DIRECTORY)
            if name not in discovered:
                return Response(
                    {"error": f"Blueprint '{name}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            library = get_user_blueprint_library()
            installed = library.setdefault("installed", [])
            if name in installed:
                # Idempotent add: already in the library.
                return Response(_serialize_entry(name), status=status.HTTP_200_OK)

            installed.append(name)
            if not save_user_blueprint_library(library):
                return Response(
                    {"error": "Failed to save blueprint library."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(_serialize_entry(name), status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Error adding blueprint to library.")
            return Response(
                {"error": "Failed to add blueprint to library."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LibraryDetailAPIView(APIView):
    """
    DELETE /v1/library/<blueprint_name>/ -> remove a blueprint from the library
    """

    permission_classes = LIBRARY_API_PERMISSIONS

    def delete(self, request, blueprint_name: str, *_args, **_kwargs):
        try:
            library = get_user_blueprint_library()
            installed = library.get("installed", [])
            if blueprint_name not in installed:
                return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

            installed.remove(blueprint_name)
            if not save_user_blueprint_library(library):
                return Response(
                    {"error": "Failed to save blueprint library."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("Error removing blueprint '%s' from library.", blueprint_name)
            return Response(
                {"error": "Failed to remove blueprint from library."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
