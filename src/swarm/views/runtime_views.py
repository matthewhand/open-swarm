"""Runtime-mode banner + browser-control catalog (REQ-45).

Both endpoints are AllowAny and secret-free: they describe where the *app*
is running and which browser *provider* is the default. They never echo
host paths, usernames, tokens, or raw unrecognized env values.
"""
from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.browser_control import catalog_payload
from swarm.core.runtime_mode import runtime_banner


class RuntimeModeView(APIView):
    """GET /v1/runtime/ — dismissible SPA banner source of truth."""

    permission_classes = [AllowAny]

    def get(self, request, *_args, **_kwargs):
        return Response(runtime_banner())


class BrowserControlView(APIView):
    """GET /v1/browser-control/ — this-machine default; sandbox/SaaS TODO."""

    permission_classes = [AllowAny]

    def get(self, request, *_args, **_kwargs):
        return Response(catalog_payload())
