"""REST surface for remote agent harnesses (Hermes, OpenMousBot, Rakazo).

GET    /v1/remotes/                 kinds catalog + configured remotes (opt-in)
POST   /v1/remotes/                 add a kind (base_url + optional api_key_env)
GET    /v1/remotes/<id>/            one remote
PATCH  /v1/remotes/<id>/            persist base_url + auth
DELETE /v1/remotes/<id>/            remove a configured remote
POST   /v1/remotes/<id>/health/     connectivity check (honest fail)
POST   /v1/remotes/<id>/operate/    list or send a job via the real API

Kind id ``omb`` stays; user-facing label is OpenMousBot, never OMB.

Permissions follow ``api_permission_classes()`` — never ``SWARM_ALLOW_ANONYMOUS``.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes
from swarm.core import remotes as remotes_core

logger = logging.getLogger(__name__)


class RemotesListView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_remotes_list",
        summary="List remote harness connections",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, _request, *_args, **_kwargs):
        specs = remotes_core.load_configured_remotes()
        return Response(
            {
                "object": "list",
                "vocabulary": remotes_core.TEAM_VOCABULARY,
                "kinds": remotes_core.kind_catalog(),
                "data": [spec.public_dict() for spec in specs.values()],
                "team_members": [
                    m
                    for m in remotes_core.list_team_members()
                    if remotes_core.is_configured(m["id"])
                ],
            }
        )

    @extend_schema(
        operation_id="v1_remotes_add",
        summary="Add a remote kind (base URL + optional api-key-env)",
        request=inline_serializer(
            name="RemoteAddRequest",
            fields={
                "kind": serializers.CharField(required=False, help_text="hermes | omb | rakazo"),
                "id": serializers.CharField(required=False, help_text="Alias of kind"),
                "base_url": serializers.CharField(required=True),
                "api_key_env": serializers.CharField(required=False, allow_blank=True),
                "ui_url": serializers.CharField(required=False, allow_blank=True),
                "cookie": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        kind = str(body.get("kind") or body.get("id") or "").strip()
        base_url = "" if body.get("base_url") is None else str(body.get("base_url"))
        if not kind:
            return Response(
                {"error": "Provide kind (hermes, omb / OpenMousBot, rakazo)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        kwargs: dict[str, str] = {}
        if body.get("api_key_env") not in (None, ""):
            kwargs["api_key_env"] = str(body["api_key_env"])
        if "ui_url" in body:
            kwargs["ui_url"] = "" if body["ui_url"] is None else str(body["ui_url"])
        if "cookie" in body:
            kwargs["cookie"] = "" if body["cookie"] is None else str(body["cookie"])
        try:
            spec, path = remotes_core.add_remote(kind, base_url=base_url, **kwargs)
        except remotes_core.RemoteError as exc:
            code = status.HTTP_404_NOT_FOUND if "Unknown remote" in str(exc) else status.HTTP_400_BAD_REQUEST
            return Response({"error": str(exc)}, status=code)
        except OSError as exc:
            logger.exception("Failed to add remote %s", kind)
            return Response({"error": f"failed to persist: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        payload = spec.public_dict()
        payload["persisted_to"] = str(path)
        return Response(payload, status=status.HTTP_201_CREATED)


class RemoteDetailView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_remotes_get",
        summary="Get one remote harness (secrets redacted)",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, _request, remote_id: str, *_args, **_kwargs):
        try:
            spec = remotes_core.load_remote(remote_id)
        except remotes_core.RemoteError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(spec.public_dict())

    @extend_schema(
        operation_id="v1_remotes_patch",
        summary="Persist base URL and auth for a remote harness",
        request=inline_serializer(
            name="RemotePatchRequest",
            fields={
                "base_url": serializers.CharField(required=False, allow_blank=True),
                "api_key": serializers.CharField(required=False, allow_blank=True),
                "api_key_env": serializers.CharField(required=False, allow_blank=True),
                "ui_url": serializers.CharField(required=False, allow_blank=True),
                "cookie": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def patch(self, request, remote_id: str, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        kwargs: dict[str, str] = {}
        for field in ("base_url", "api_key", "api_key_env", "ui_url", "cookie"):
            if field in body:
                kwargs[field] = "" if body[field] is None else str(body[field])
        if not kwargs:
            return Response(
                {"error": "Provide at least one of base_url, api_key, api_key_env, ui_url, cookie."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            spec, path = remotes_core.persist_remote(remote_id, **kwargs)
        except remotes_core.RemoteError as exc:
            code = status.HTTP_404_NOT_FOUND if "Unknown remote" in str(exc) else status.HTTP_400_BAD_REQUEST
            return Response({"error": str(exc)}, status=code)
        except OSError as exc:
            logger.exception("Failed to persist remotes.%s", remote_id)
            return Response({"error": f"failed to persist: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        payload = spec.public_dict()
        payload["persisted_to"] = str(path)
        return Response(payload)

    @extend_schema(
        operation_id="v1_remotes_delete",
        summary="Remove a configured remote",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, _request, remote_id: str, *_args, **_kwargs):
        try:
            rid, path = remotes_core.remove_remote(remote_id)
        except remotes_core.RemoteError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except OSError as exc:
            logger.exception("Failed to remove remotes.%s", remote_id)
            return Response({"error": f"failed to persist: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"id": rid, "removed": True, "persisted_to": str(path)})


class RemoteHealthView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_remotes_health",
        summary="Probe a remote harness (health/version). Honest fail if down.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, _request, remote_id: str, *_args, **_kwargs):
        try:
            remotes_core._require_id(remote_id)
        except remotes_core.RemoteError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        result = remotes_core.check_health(remote_id)
        # 200 even when DOWN — this is a probe report, not a crash.
        return Response(result.as_dict(), status=status.HTTP_200_OK)

    def get(self, request, remote_id: str, *_args, **_kwargs):
        return self.post(request, remote_id)


class RemoteOperateView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_remotes_operate",
        summary="List or send a job via the remote harness's real API",
        request=inline_serializer(
            name="RemoteOperateRequest",
            fields={
                "op": serializers.CharField(required=False, help_text="list or send"),
                "prompt": serializers.CharField(required=False, allow_blank=True),
                "target": serializers.CharField(required=False, allow_blank=True, help_text="OpenMousBot/Rakazo bot id"),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def post(self, request, remote_id: str, *_args, **_kwargs):
        try:
            remotes_core._require_id(remote_id)
        except remotes_core.RemoteError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        body = request.data if isinstance(request.data, dict) else {}
        result = remotes_core.operate(
            remote_id,
            str(body.get("op") or "list"),
            prompt=str(body.get("prompt") or ""),
            target=str(body.get("target") or body.get("bot_id") or ""),
        )
        return Response(result.as_dict(), status=status.HTTP_200_OK)


class AgentTeamView(APIView):
    """Handoff Team roster — remotes (and later CLI/API agents) that see/talk.

    Distinct from ``/v1/teams/`` (LLM-profile aliases / Profiles).
    """

    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_agent_team_get",
        summary="Handoff Team members (not /v1/teams/ Profiles)",
        description=(
            "A Team wires API, CLI, and remote agents so they can see and talk "
            "via openai-agents handoff / as_tool. This is not the /v1/teams/ "
            "LLM-profile alias registry."
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, _request, *_args, **_kwargs):
        return Response(remotes_core.agent_team_public())

    @extend_schema(
        operation_id="v1_agent_team_patch",
        summary="Place remotes into the handoff Team",
        request=inline_serializer(
            name="AgentTeamPatchRequest",
            fields={
                "members": serializers.ListField(
                    child=serializers.CharField(),
                    required=False,
                    help_text="Full roster of remote ids (hermes, omb, rakazo).",
                ),
                "place": serializers.CharField(
                    required=False, allow_blank=True, help_text="Remote id to add"
                ),
                "unplace": serializers.CharField(
                    required=False, allow_blank=True, help_text="Remote id to remove"
                ),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        try:
            if "members" in body:
                raw = body.get("members")
                if isinstance(raw, str):
                    raw = [part.strip() for part in raw.split(",") if part.strip()]
                if not isinstance(raw, list):
                    return Response(
                        {"error": "members must be a list of remote ids."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                _members, path = remotes_core.persist_agent_team([str(item) for item in raw])
            elif body.get("place"):
                _members, path = remotes_core.place_team_member(str(body["place"]))
            elif body.get("unplace"):
                _members, path = remotes_core.unplace_team_member(str(body["unplace"]))
            else:
                return Response(
                    {"error": "Provide members, place, or unplace."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except remotes_core.RemoteError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError as exc:
            logger.exception("Failed to persist agent_team")
            return Response(
                {"error": f"failed to persist: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        payload = remotes_core.agent_team_public()
        payload["persisted_to"] = str(path)
        return Response(payload)
