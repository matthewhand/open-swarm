"""Agents page: prefer the React SPA, fall back to the Django template."""

from pathlib import Path

from django.http import FileResponse
from django.shortcuts import render


def agent_router_page(request):
    index = Path("webui/frontend/dist/index.html")
    if index.is_file():
        return FileResponse(index.open("rb"), content_type="text/html")
    return render(request, "agent_router.html")
