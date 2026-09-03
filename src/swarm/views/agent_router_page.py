"""Agents page: prefer the React SPA, fall back to the Django template."""

from pathlib import Path

from django.shortcuts import render
from swarm.views.web_views import asgi_file_response


def agent_router_page(request):
    index = Path("webui/frontend/dist/index.html")
    if index.is_file():
        return asgi_file_response(index, "text/html")
    return render(request, "agent_router.html")
