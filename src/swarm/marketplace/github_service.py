"""GitHub marketplace discovery service (skeleton).

Provides functions to search repositories by topics and normalize repo + manifest
data into marketplace items. Real HTTP calls are intentionally omitted here;
tests monkeypatch these functions to return controlled data.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def search_repos_by_topics(
    topics: List[str],
    orgs: Optional[List[str]] = None,
    *,
    sort: str = 'stars',
    order: str = 'desc',
    query: str = '',
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return a list of repo dicts { 'full_name': str, 'html_url': str, ... }.

    This is a placeholder; tests mock this function. In production, implement
    GitHub REST or GraphQL calls with rate limit handling and caching.
    """
    return []


def fetch_repo_manifests(
    repo: Dict[str, Any],
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return list of manifest items found in a repository.

    Placeholder for tests; production should fetch conventional paths like
    open-swarm.json or swarm/blueprints/*/manifest.json and swarm/mcp/*/manifest.json.
    """
    return []


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

