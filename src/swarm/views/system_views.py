"""Read-only System facts for the Settings overlay (REQ-56)."""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core.local_store import NOT_CREATED, local_store_facts

logger = logging.getLogger(__name__)


class LocalStoreView(APIView):
    """GET /v1/system/ — local store size, path, and counts. Read-only."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_system_local_store",
        summary="Local store facts",
        description=(
            "Read-only facts about the local database on this machine: "
            "human-readable file size, a home-relative (non-secret) path, "
            "conversation count, and message count. Missing store returns "
            "0 / not created yet. Never returns a connection string."
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        try:
            facts = local_store_facts()
        except Exception:
            logger.exception("Failed to collect local store facts")
            facts = {
                "path": NOT_CREATED,
                "size_bytes": 0,
                "size_label": NOT_CREATED,
                "created": False,
                "conversation_count": 0,
                "message_count": 0,
            }
        return Response(facts)
