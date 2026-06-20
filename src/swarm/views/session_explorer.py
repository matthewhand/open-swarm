"""Session Explorer web UI.

Browse the stateful ``/v1/responses`` session records persisted by
:mod:`swarm.core.responses_store` — including the per-delegation ``progress``
timeline produced by hybrid_team's parallel claude-orchestrated delegation. A
read-only observability surface: session list + a per-session detail with the
inter-agent delegation timeline.
"""
from __future__ import annotations

from django.http import Http404, JsonResponse
from django.shortcuts import render

from swarm.core import responses_store


def session_explorer(request):
    """Session list page."""
    sessions = responses_store.list_summaries()
    counts: dict[str, int] = {}
    for s in sessions:
        counts[s.get("status") or "unknown"] = counts.get(s.get("status") or "unknown", 0) + 1
    return render(request, "session_explorer.html", {
        "sessions": sessions,
        "total": len(sessions),
        "status_counts": counts,
    })


def session_detail(request, response_id: str):
    """Per-session detail: status, output, and the delegation timeline."""
    record = responses_store.load(response_id)
    if record is None:
        raise Http404(f"Session '{response_id}' not found")
    resp = record.get("response") or {}
    return render(request, "session_detail.html", {
        "session": resp,
        "messages": record.get("messages") or [],
        "delegations": resp.get("progress") or [],
    })


def session_list_api(request):
    """JSON feed of session summaries (used for live refresh / external tools)."""
    return JsonResponse({"sessions": responses_store.list_summaries()})
