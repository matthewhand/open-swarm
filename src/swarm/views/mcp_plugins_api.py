"""REST surface for Plugins MCP manage (#502 / #750).

GET    /v1/mcp-plugins/           redacted server list + discovered tools
POST   /v1/mcp-plugins/           upsert one local/remote/OpenAPI server
DELETE /v1/mcp-plugins/<name>/    remove a server
POST   /v1/mcp-plugins/discover/  connect and list_tools (honest error)

Persists through ADR-002 ``mcpServers``. Secrets stay ``${VAR}``. Responses
never include secret values. Distinct from ``ENABLE_MCP_SERVER`` / ``/mcp/``.
OpenAPI servers use ``mcp-openapi-proxy`` (source=openapi).
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
from swarm.core import mcp_plugins as plugins

logger = logging.getLogger(__name__)


def _error(exc: Exception) -> Response:
    if isinstance(exc, plugins.McpPluginError):
        return Response({"error": str(exc), "code": exc.code}, status=exc.status)
    if isinstance(exc, ownership.ConfigOwnershipError):
        return Response({"error": str(exc), "code": exc.code}, status=exc.status)
    logger.exception("MCP plugins API failed")
    return Response(
        {"error": "MCP plugins request failed.", "code": "mcp_plugin_error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _payload(config: dict | None = None) -> dict:
    cfg = config if isinstance(config, dict) else plugins.swarm_config()
    servers = plugins.load_mcp_servers(cfg)
    return {
        "object": "mcp_plugins",
        "scope": "global_servers_per_chat_tools",
        "servers": [plugins.public_server(name, spec) for name, spec in servers.items()],
    }


class McpPluginsView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_mcp_plugins_get",
        summary="List configured MCP plugin servers (redacted)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, _request, *_args, **_kwargs):
        try:
            return Response(_payload())
        except Exception as exc:
            return _error(exc)

    @extend_schema(
        operation_id="v1_mcp_plugins_post",
        summary="Upsert one local, remote, or OpenAPI MCP plugin server",
        request=inline_serializer(
            name="McpPluginUpsertRequest",
            fields={
                "name": serializers.CharField(),
                "kind": serializers.CharField(required=False),
                "source": serializers.CharField(required=False, allow_blank=True),
                "command": serializers.CharField(required=False, allow_blank=True),
                "args": serializers.ListField(required=False, child=serializers.CharField()),
                "url": serializers.CharField(required=False, allow_blank=True),
                "openapi_spec_url": serializers.CharField(required=False, allow_blank=True),
                "enabled": serializers.BooleanField(required=False),
                "env": serializers.DictField(required=False),
                "headers": serializers.DictField(required=False),
                "provides": serializers.ListField(required=False, child=serializers.CharField()),
                "note": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name") or "").strip()
        if not name:
            return Response(
                {"error": "name is required.", "code": "bad_payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            spec = plugins.normalize_plugin_spec(body, name=name)
            ownership.persist_webui_section(
                "mcpServers",
                upsert={spec["name"]: plugins.spec_to_config_entry(spec)},
            )
            return Response(_payload())
        except Exception as exc:
            return _error(exc)


class McpPluginDetailView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_mcp_plugins_delete",
        summary="Remove one MCP plugin server from swarm_config",
        responses={200: OpenApiTypes.OBJECT},
    )
    def delete(self, _request, name: str, *_args, **_kwargs):
        key = str(name or "").strip()
        if not key:
            return Response(
                {"error": "name is required.", "code": "bad_payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ownership.persist_webui_section("mcpServers", delete=[key])
            return Response(_payload())
        except Exception as exc:
            return _error(exc)


class McpPluginDiscoverView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    @extend_schema(
        operation_id="v1_mcp_plugins_discover",
        summary="Connect to an MCP server and list tools (name + description)",
        request=inline_serializer(
            name="McpPluginDiscoverRequest",
            fields={
                "name": serializers.CharField(required=False, allow_blank=True),
                "kind": serializers.CharField(required=False),
                "source": serializers.CharField(required=False, allow_blank=True),
                "command": serializers.CharField(required=False, allow_blank=True),
                "args": serializers.ListField(required=False, child=serializers.CharField()),
                "url": serializers.CharField(required=False, allow_blank=True),
                "openapi_spec_url": serializers.CharField(required=False, allow_blank=True),
                "env": serializers.DictField(required=False),
                "headers": serializers.DictField(required=False),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 502: OpenApiTypes.OBJECT},
    )
    def post(self, request, *_args, **_kwargs):
        body = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name") or "").strip()
        cfg = plugins.swarm_config()
        try:
            tools, spec = plugins.discover_and_store(
                name or str(body.get("command") or body.get("url") or "server"),
                body,
                config=cfg,
                persist=bool(name and name in plugins.load_mcp_servers(cfg)),
            )
        except Exception as exc:
            return _error(exc)
        return Response(
            {
                "object": "mcp_plugin_tools",
                "name": spec.get("name") or name,
                "kind": spec.get("kind"),
                "source": spec.get("source"),
                "tools": tools,
            }
        )
