"""REST for Settings image-gen + per-agent still avatars (REQ-83 / #436).

GET/PATCH ``/v1/image-gen/`` — base URL, model id, api-key env name only.
POST ``/v1/agents/<id>/avatar/generate/`` — still avatar from the configured
OpenAI-compatible ``/v1/images/generations`` endpoint.

Empty/off never guesses a host. Responses never include live tokens.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core import image_gen as image_gen_core
from swarm.core.chat_store import normalize_agent_id

logger = logging.getLogger(__name__)


def _settings_payload(probe: bool = True) -> dict:
    spec = image_gen_core.load_settings()
    if probe:
        payload = image_gen_core.probe_status(spec)
    else:
        payload = spec.public_dict()
        if spec.configured():
            payload["status"] = "unknown"
            payload["detail"] = "Image generation is configured. Status was not probed."
        else:
            payload["status"] = "off"
            payload["detail"] = (
                "Image generation is off. No host is used until you set a base URL."
            )
    payload["avatars"] = image_gen_core.load_avatar_map()
    return payload


class ImageGenSettingsView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_image_gen_get",
        summary="Image generation settings (env name only, no secrets)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, *_args, **_kwargs):
        probe = str(request.query_params.get("probe") or "1").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        return Response(_settings_payload(probe=probe))

    @extend_schema(
        operation_id="v1_image_gen_patch",
        summary="Persist image-gen base URL, model, and api-key env name",
        request=inline_serializer(
            name="ImageGenPatchRequest",
            fields={
                "base_url": serializers.CharField(required=False, allow_blank=True),
                "model": serializers.CharField(required=False, allow_blank=True),
                "api_key_env": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        kwargs: dict[str, str] = {}
        for field in ("base_url", "model", "api_key_env"):
            if field in body:
                kwargs[field] = "" if body[field] is None else str(body[field])
        if "api_key" in body:
            return Response(
                {"error": "Send api_key_env (environment variable name) only. Never a live token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not kwargs:
            return Response(
                {"error": "Provide at least one of base_url, model, api_key_env."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            spec, path = image_gen_core.persist_settings(**kwargs)
        except image_gen_core.ImageGenError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError as exc:
            logger.exception("Failed to persist image_gen")
            return Response(
                {"error": f"failed to persist: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        payload = image_gen_core.probe_status(spec)
        payload["avatars"] = image_gen_core.load_avatar_map()
        payload["persisted_to"] = str(path)
        return Response(payload)


class AgentAvatarGenerateView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_agent_avatar_generate",
        summary="Generate a still avatar for one agent via the configured image-gen endpoint",
        request=inline_serializer(
            name="AgentAvatarGenerateRequest",
            fields={
                "prompt": serializers.CharField(required=False, allow_blank=True),
                "name": serializers.CharField(required=False, allow_blank=True),
                "role": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, agent_id: str, *_args, **_kwargs):
        agent = normalize_agent_id(agent_id)
        body = request.data if isinstance(request.data, dict) else {}
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            prompt = image_gen_core.default_avatar_prompt(
                str(body.get("name") or agent),
                str(body.get("role") or ""),
            )
        spec = image_gen_core.load_settings()
        if not spec.configured():
            return Response(
                {
                    "error": (
                        "Image generation is not configured. "
                        "Open Settings → Image generation and set a base URL."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            avatar_path = image_gen_core.generate_and_store(agent, prompt, settings=spec)
        except image_gen_core.ImageGenError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError as exc:
            logger.exception("Failed to store still avatar for %s", agent)
            return Response(
                {"error": f"failed to store avatar: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {
                "object": "agent_avatar",
                "agent_id": agent,
                "avatar_path": avatar_path,
                "still": True,
                "prompt": prompt,
            }
        )
