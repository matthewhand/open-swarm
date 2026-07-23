"""Session Explorer web UI.

Browse the stateful ``/v1/responses`` session records persisted by
:mod:`swarm.core.responses_store` — including the per-delegation ``progress``
timeline produced by hybrid_team's parallel claude-orchestrated delegation. A
read-only observability surface: session list + a per-session detail with the
inter-agent delegation timeline.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import render

from swarm.auth import request_principal
from swarm.core import responses_store

# Default page size for first paint + live poll. Hard ceiling prevents multi-MB
# responses when stores grow large.
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500


def _parse_limit(request, default: int = _DEFAULT_LIMIT) -> int:
    try:
        return max(1, min(_MAX_LIMIT, int(request.GET.get("limit", str(default)))))
    except (TypeError, ValueError):
        return default


def _session_inventory(request) -> tuple[list[dict], dict[str, int]]:
    """Principal-scoped inventory (newest first) + status counts.

    ``limit=None`` so totals are not silently capped at the store helper's
    default of 200. Sessions without an owner, or owned by another principal,
    are excluded via :func:`responses_store.owner_allows` (fail-closed).
    """
    principal = request_principal(request)
    all_sessions = [
        s for s in responses_store.list_summaries(limit=None)
        if responses_store.owner_allows(s, principal)
    ]
    counts: dict[str, int] = {}
    for s in all_sessions:
        key = s.get("status") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return all_sessions, counts


@login_required
def session_explorer(request):
    """Session list page (authenticated — transcripts may contain secrets)."""
    all_sessions, counts = _session_inventory(request)
    limit = _parse_limit(request)
    sessions = all_sessions[:limit]
    total = len(all_sessions)
    return render(request, "session_explorer.html", {
        "sessions": sessions,
        "total": total,
        "shown": len(sessions),
        "limit": limit,
        "truncated": total > limit,
        "status_counts": counts,
    })


@login_required
def session_detail(request, response_id: str):
    """Per-session detail: status, output, and the delegation timeline."""
    record = responses_store.load(response_id)
    if record is None:
        raise Http404(f"Session '{response_id}' not found")
    principal = request_principal(request)
    if not responses_store.owner_allows(record, principal):
        raise Http404(f"Session '{response_id}' not found")
    resp = record.get("response") or {}
    return render(request, "session_detail.html", {
        "session": resp,
        "messages": record.get("messages") or [],
        "delegations": resp.get("progress") or [],
    })


@login_required
def session_list_api(request):
    """JSON feed of session summaries (live refresh).

    Honours the same ``?limit=`` contract as the HTML explorer so the default-
    checked 3s poll cannot blow past the first-paint cap and desync the banner.
    """
    all_sessions, counts = _session_inventory(request)
    limit = _parse_limit(request)
    sessions = all_sessions[:limit]
    total = len(all_sessions)
    return JsonResponse({
        "sessions": sessions,
        "total": total,
        "shown": len(sessions),
        "limit": limit,
        "truncated": total > limit,
        "status_counts": counts,
    })
