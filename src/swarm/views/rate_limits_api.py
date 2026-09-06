"""REST surface for REQ-88 provider rate limits.

GET    /v1/rate-limits/     configured providers + user-defined rules
PATCH  /v1/rate-limits/     persist rules onto that provider row

SoT is local swarm_config.json (not Neon). Responses never include secrets.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core import provider_rate_limit as rate_limits

logger = logging.getLogger(__name__)


def _payload(config=None) -> dict:
    rows = rate_limits.list_provider_rate_limits(config)
    return {
        "object": "provider_rate_limits",
        "data": rows,
        "rules": list(rate_limits.RULE_KEYS),
        "note": "Empty values mean no limit. Agents that send through a provider share one queue.",
    }


class RateLimitsView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_rate_limits_get",
        summary="List provider rate-limit rules (local config, not Neon)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, _request, *_args, **_kwargs):
        try:
            return Response(_payload())
        except Exception:
            logger.exception("Failed to load provider rate limits")
            return Response(
                {
                    "object": "provider_rate_limits",
                    "data": [],
                    "rules": list(rate_limits.RULE_KEYS),
                    "warnings": ["Failed to load provider rate limits."],
                },
                status=status.HTTP_200_OK,
            )

    @extend_schema(
        operation_id="v1_rate_limits_patch",
        summary="Persist user-defined rate limits on a provider",
        request=inline_serializer(
            name="RateLimitsPatchRequest",
            fields={
                "provider": serializers.CharField(required=False),
                "id": serializers.CharField(required=False),
                "rules": serializers.DictField(required=False),
                "messages_per_minute": serializers.IntegerField(required=False, allow_null=True),
                "requests_per_minute": serializers.IntegerField(required=False, allow_null=True),
                "tokens_per_minute": serializers.IntegerField(required=False, allow_null=True),
                "tokens_per_day": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        provider = body.get("provider") or body.get("id") or body.get("provider_key")
        if not isinstance(provider, str) or not provider.strip():
            return Response(
                {"error": "Provide provider as cli:<name>, llm:<id>, or remote:<id>."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw_rules = body.get("rules") if isinstance(body.get("rules"), dict) else {}
        merged = dict(raw_rules)
        for key in rate_limits.RULE_KEYS:
            if key in body:
                merged[key] = body.get(key)
        try:
            parsed, path = rate_limits.persist_provider_rate_limits(provider, merged)
        except Exception as exc:
            from swarm.core.config_ownership import ConfigOwnershipError

            if isinstance(exc, ConfigOwnershipError):
                return Response(
                    {"error": str(exc), "code": exc.code},
                    status=exc.status,
                )
            logger.exception("Failed to persist provider rate limits")
            return Response(
                {"error": "Could not persist rate limits."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        payload = _payload()
        payload["saved"] = parsed.public_dict()
        payload["provider"] = rate_limits.normalize_provider_key(provider)
        payload["persisted_to"] = str(path)
        return Response(payload)
