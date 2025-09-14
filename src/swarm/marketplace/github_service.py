"""GitHub marketplace discovery service (skeleton).

Provides functions to search repositories by topics and normalize repo + manifest
data into marketplace items. Real HTTP calls are intentionally omitted here;
tests monkeypatch these functions to return controlled data.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
import base64
import httpx
import time

GITHUB_API = "https://api.github.com"

# Very simple in-process cache (best-effort) to reduce GitHub calls in a
# long-lived process. Keys are based on query parameters. TTL is short.
_CACHE: Dict[Tuple[str, str, str, str], Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 300.0


def search_repos_by_topics(
    topics: List[str],
    orgs: Optional[List[str]] = None,
    *,
    sort: str = 'stars',
    order: str = 'desc',
    query: str = '',
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search public GitHub repositories by topics/orgs with optional name query.

    Returns a subset of fields for each repo. This function is safe to mock in
    tests; on failure it returns an empty list.
    """
    try:
        q_parts = []
        for t in topics or []:
            if t:
                q_parts.append(f"topic:{t}")
        for o in orgs or []:
            if o:
                q_parts.append(f"org:{o}")
        if query:
            # Name search qualifier
            q_parts.append(f"{query} in:name")
        q = " ".join(q_parts) or "open-swarm-blueprint open-swarm-mcp-template"

        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        sort = sort or "stars"
        order = order or "desc"
        params = {"q": q, "sort": sort, "order": order, "per_page": 20}

        # Cache key and fast path
        ck = (q, sort, order, "20")
        now = time.monotonic()
        cached = _CACHE.get(ck)
        if cached and (now - cached[0] < _CACHE_TTL_SECONDS):
            return cached[1]
        with httpx.Client(timeout=10.0, headers=headers) as client:
            resp = client.get(f"{GITHUB_API}/search/repositories", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json() or {}
            items = data.get("items") or []
            out: List[Dict[str, Any]] = []
            for it in items:
                out.append({
                    "full_name": it.get("full_name"),
                    "html_url": it.get("html_url"),
                })
            _CACHE[ck] = (now, out)
            return out
    except Exception:
        return []


def fetch_repo_manifests(
    repo: Dict[str, Any],
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return list of manifest items found in a repository.

    Tries the top-level `open-swarm.json` first. Then lists conventional
    directories for per-item manifests. On any error, returns partial results.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    results: List[Dict[str, Any]] = []
    try:
        full = (repo.get("full_name") or "").split("/")
        if len(full) != 2:
            return results
        owner, name = full
        with httpx.Client(timeout=10.0, headers=headers) as client:
            # Try top-level open-swarm.json
            top = client.get(f"{GITHUB_API}/repos/{owner}/{name}/contents/open-swarm.json")
            if top.status_code == 200:
                data = top.json()
                if isinstance(data, dict) and data.get("type") == "file":
                    content = data.get("content")
                    if content:
                        try:
                            decoded = base64.b64decode(content).decode("utf-8")
                            # Expecting either a single item or a list of items
                            import json
                            parsed = json.loads(decoded)
                            if isinstance(parsed, list):
                                results.extend(parsed)
                            elif isinstance(parsed, dict):
                                results.append(parsed)
                        except Exception:
                            pass
            # List per-item manifests under conventional paths
            for base in ("swarm/blueprints", "swarm/mcp"):
                resp = client.get(f"{GITHUB_API}/repos/{owner}/{name}/contents/{base}")
                if resp.status_code != 200:
                    continue
                entries = resp.json() or []
                for ent in entries:
                    if not isinstance(ent, dict) or ent.get("type") != "dir":
                        continue
                    path = ent.get("path")
                    if not path:
                        continue
                    man = client.get(f"{GITHUB_API}/repos/{owner}/{name}/contents/{path}/manifest.json")
                    if man.status_code == 200:
                        mdata = man.json()
                        if isinstance(mdata, dict) and mdata.get("type") == "file":
                            content = mdata.get("content")
                            if content:
                                try:
                                    decoded = base64.b64decode(content).decode("utf-8")
                                    import json
                                    parsed = json.loads(decoded)
                                    if isinstance(parsed, dict):
                                        results.append(parsed)
                                except Exception:
                                    pass
    except Exception:
        return results
    return results


def to_marketplace_items(
    repo: Dict[str, Any],
    items: Iterable[Dict[str, Any]],
    *,
    kind: str,
) -> List[Dict[str, Any]]:
    """Normalize repo + manifest items into a common marketplace item shape.

    kind: 'blueprint' or 'mcp'
    """
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append(
            {
                'repo_full_name': repo.get('full_name'),
                'repo_url': repo.get('html_url'),
                'kind': kind,
                'name': it.get('name'),
                'description': it.get('description', ''),
                'version': it.get('version', ''),
                'tags': it.get('tags', []),
                'manifest': it,
            }
        )
    return out
