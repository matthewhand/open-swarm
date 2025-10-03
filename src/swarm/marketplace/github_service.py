"""GitHub marketplace discovery service (skeleton).

Provides functions to search repositories by topics and normalize repo + manifest
data into marketplace items. Real HTTP calls are intentionally omitted here;
tests monkeypatch these functions to return controlled data.
"""
from __future__ import annotations

import ast
import base64
import json as _json
import time
from collections.abc import Iterable
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"

# Very simple in-process cache (best-effort) to reduce GitHub calls in a
# long-lived process. Keys are based on query parameters. TTL is short.
_CACHE: dict[tuple[str, str, str, str], tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 300.0


def search_repos_by_topics(
    topics: list[str],
    orgs: list[str] | None = None,
    *,
    sort: str = 'stars',
    order: str = 'desc',
    query: str = '',
    token: str | None = None,
) -> list[dict[str, Any]]:
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
            out: list[dict[str, Any]] = []
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
    repo: dict[str, Any],
    token: str | None = None,
) -> list[dict[str, Any]]:
    """Return list of manifest items found in a repository.

    Tries the top-level `open-swarm.json` first. Then lists conventional
    directories for per-item manifests. On any error, returns partial results.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    results: list[dict[str, Any]] = []
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
                                    parsed = _json.loads(decoded)
                                    if isinstance(parsed, dict):
                                        # Enrich with metrics and owner
                                        enrich_item_with_metrics(client, owner, name, path, parsed)
                                        parsed.setdefault('owner', owner)
                                        results.append(parsed)
                                except Exception:
                                    pass
    except Exception:
        return results
    return results


def enrich_item_with_metrics(client: httpx.Client, owner: str, repo: str, item_dir: str, item: dict[str, Any]) -> None:
    """Compute file and line counts; extract metadata from python file if possible.

    This function is best-effort; failures are silently ignored.
    """
    try:
        listing = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{item_dir}")
        if listing.status_code != 200:
            return
        entries = listing.json() or []
        file_count = 0
        line_total = 0
        first_py_content = None
        for f in entries:
            if not isinstance(f, dict) or f.get('type') != 'file':
                continue
            file_count += 1
            # Count lines for small files (< 200KB) to avoid heavy downloads
            size = f.get('size') or 0
            if size and size < 200_000:
                # Fetch file content and count lines
                fc = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{f.get('path')}")
                if fc.status_code == 200:
                    fj = fc.json()
                    try:
                        raw = base64.b64decode(fj.get('content') or b'').decode('utf-8', errors='ignore')
                        line_total += raw.count('\n') + 1
                        if (f.get('name') or '').endswith('.py') and first_py_content is None:
                            first_py_content = raw
                    except Exception:
                        pass
        item.setdefault('file_count', file_count)
        item.setdefault('line_count', line_total)
        # Try AST parse for metadata name/description if missing
        if first_py_content and (not item.get('name') or not item.get('description')):
            meta = safe_extract_metadata_from_py(first_py_content)
            if meta:
                item.setdefault('name', meta.get('name'))
                item.setdefault('description', meta.get('description'))
    except Exception:
        return


def safe_extract_metadata_from_py(src: str) -> dict[str, Any] | None:
    """Safely extract Blueprint.metadata dict from Python source using AST only.

    Looks for a class definition with a 'metadata' attribute assigned to a dict
    literal. Does not execute any code.
    """
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for body in node.body:
                    if isinstance(body, ast.Assign):
                        for target in body.targets:
                            if isinstance(target, ast.Name) and target.id == 'metadata':
                                if isinstance(body.value, ast.Dict):
                                    keys = []
                                    vals = []
                                    for k in body.value.keys:
                                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                            keys.append(k.value)
                                        else:
                                            keys.append(None)
                                    for v in body.value.values:
                                        if isinstance(v, ast.Constant):
                                            vals.append(v.value)
                                        else:
                                            vals.append(None)
                                    md = {k: v for k, v in zip(keys, vals, strict=False) if k}
                                    # Only return if we got at least a name/description
                                    if md.get('name') or md.get('description'):
                                        return md
        return None
    except Exception:
        return None


def to_marketplace_items(
    repo: dict[str, Any],
    items: Iterable[dict[str, Any]],
    *,
    kind: str,
) -> list[dict[str, Any]]:
    """Normalize repo + manifest items into a common marketplace item shape.

    kind: 'blueprint' or 'mcp'
    """
    out: list[dict[str, Any]] = []
    for it in items:
        out.append(
            {
                'repo_full_name': repo.get('full_name'),
                'repo_url': repo.get('html_url'),
                'owner': it.get('owner'),
                'kind': kind,
                'name': it.get('name'),
                'description': it.get('description', ''),
                'version': it.get('version', ''),
                'tags': it.get('tags', []),
                'file_count': it.get('file_count'),
                'line_count': it.get('line_count'),
                'manifest': it,
            }
        )
    return out
