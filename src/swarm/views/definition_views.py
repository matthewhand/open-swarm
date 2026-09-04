"""REQ-42 definition context + default-LLM summarise API."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core.definition_explain import (
    DEFINITION_KINDS,
    build_definition,
    summarise_definition,
)


class DefinitionDetailView(APIView):
    """GET /v1/definitions/<kind>/<id>/ — source + injected context + LLM status."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, kind: str, definition_id: str, *_args, **_kwargs):
        if kind not in DEFINITION_KINDS:
            return Response({"error": "unknown kind"}, status=status.HTTP_404_NOT_FOUND)
        extra = request.query_params.get("extra")
        role = request.query_params.get("role")
        return Response(
            build_definition(kind, definition_id, extra=extra, role=role),
            status=status.HTTP_200_OK,
        )


class DefinitionSummarizeView(APIView):
    """POST /v1/definitions/<kind>/<id>/summarize — default LLM only."""

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def post(self, request, kind: str, definition_id: str, *_args, **_kwargs):
        if kind not in DEFINITION_KINDS:
            return Response({"error": "unknown kind"}, status=status.HTTP_404_NOT_FOUND)
        body = request.data or {}
        source = body.get("source")
        extra = body.get("extra")
        role = body.get("role")
        result = summarise_definition(
            kind,
            definition_id,
            source_override=source if isinstance(source, str) else None,
            extra=extra if isinstance(extra, str) else None,
            role=role if isinstance(role, str) else None,
        )
        return Response(result, status=status.HTTP_200_OK)
