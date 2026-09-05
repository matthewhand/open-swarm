"""REST surface for #776 config ownership (Full coverage / hybrid).

GET    /v1/config-ownership/              inventory + decision + force-env
GET    /v1/config/sections/<section>/     redacted WebUI-owned section
PATCH  /v1/config/sections/<section>/     persist WebUI-owned section

Out-of-partition keys (secrets, HOST/PORT, DJANGO_*) are refused.
Plaintext secrets are refused. Responses never include secret values.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core import config_ownership as ownership

logger = logging.getLogger(__name__)


def _error_response(exc: ownership.ConfigOwnershipError) -> Response:
    return Response(
        {"error": str(exc), "code": exc.code},
        status=exc.status,
    )


class ConfigOwnershipView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_config_ownership_get",
        summary="Config ownership inventory (Full coverage / secrets env-only)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, _request, *_args, **_kwargs):
        try:
            return Response(ownership.ownership_payload())
        except Exception:
            logger.exception("Failed to load config ownership inventory")
            return Response(
                {"error": "failed to load config ownership"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConfigSectionView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_config_section_get",
        summary="Read one WebUI-owned swarm_config section (secrets redacted)",
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def get(self, _request, section: str, *_args, **_kwargs):
        try:
            data = ownership.public_section(section)
        except ownership.ConfigOwnershipError as exc:
            return _error_response(exc)
        return Response(
            {
                "object": "config_section",
                "section": section,
                "partition": "webui",
                "advanced": section in ownership.ADVANCED_SECTIONS,
                "settings_section": ownership.SETTINGS_PANES.get(section, "system"),
                "data": data,
                "force_env": ownership.force_env_enabled(),
            }
        )

    @extend_schema(
        operation_id="v1_config_section_patch",
        summary="Persist one WebUI-owned swarm_config section",
        request=inline_serializer(
            name="ConfigSectionPatchRequest",
            fields={
                "entries": serializers.DictField(required=False),
                "upsert": serializers.DictField(required=False),
                "delete": serializers.ListField(required=False, child=serializers.CharField()),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def patch(self, request, section: str, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        if not any(key in body for key in ("entries", "upsert", "delete")):
            return Response(
                {"error": "Provide at least one of entries, upsert, delete."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        delete = body.get("delete") if "delete" in body else None
        if delete is not None and not isinstance(delete, (list, str)):
            return Response(
                {"error": "delete must be a name or a list of names."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entries = body.get("entries") if "entries" in body else None
        upsert = body.get("upsert") if "upsert" in body else None
        if entries is not None and not isinstance(entries, dict):
            return Response({"error": "entries must be an object."}, status=status.HTTP_400_BAD_REQUEST)
        if upsert is not None and not isinstance(upsert, dict):
            return Response({"error": "upsert must be an object."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data, path = ownership.persist_webui_section(
                section,
                entries=entries,
                upsert=upsert,
                delete=delete,
            )
        except ownership.ConfigOwnershipError as exc:
            return _error_response(exc)
        except OSError as exc:
            logger.exception("Failed to persist config section %s", section)
            return Response(
                {"error": f"failed to persist: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {
                "object": "config_section",
                "section": section,
                "partition": "webui",
                "advanced": section in ownership.ADVANCED_SECTIONS,
                "data": ownership.redact_for_api(data),
                "persisted_to": str(path),
                "force_env": ownership.force_env_enabled(),
            }
        )
