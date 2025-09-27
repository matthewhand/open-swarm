"""
Enhanced GitHub client service for marketplace operations.

This module provides enhanced functionality for interacting with GitHub APIs
to discover, fetch, and manage marketplace items including blueprints and
MCP configuration templates.
"""

from __future__ import annotations

import ast
import base64
import json as _json
import time
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Tuple

import httpx
from django.db import models

from swarm.models.core_models import Blueprint, MCPConfig
from swarm.settings import (
    GITHUB_MARKETPLACE_ORG_ALLOWLIST,
    GITHUB_MARKETPLACE_TOPICS,
    GITHUB_TOKEN,
)

GITHUB_API = "https://api.github.com"

# Very simple in-process cache (best-effort) to reduce GitHub calls in a
# long-lived process. Keys are based on query parameters. TTL is short.
_CACHE: Dict[Tuple[str, str, str, str], Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 300.0


def search_repos_by_topics(
    topics: List[str],
    orgs: List[str] | None = None,
    *,
    sort: str = 'stars',
    order: str = 'desc',
    query: str = '',
    token: str | None = None,
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
                    "description": it.get("description"),
                    "stargazers_count": it.get("stargazers_count"),
                    "updated_at": it.get("updated_at"),
                    "topics": it.get("topics", []),
                })
            _CACHE[ck] = (now, out)
            return out
    except Exception:
        return []


def fetch_repo_manifests(
    repo: Dict[str, Any],
    token: str | None = None,
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


def enrich_item_with_metrics(client: httpx.Client, owner: str, repo: str, item_dir: str, item: Dict[str, Any]) -> None:
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


def safe_extract_metadata_from_py(src: str) -> Dict[str, Any] | None:
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
                                    md = {k: v for k, v in zip(keys, vals) if k}
                                    # Only return if we got at least a name/description
                                    if md.get('name') or md.get('description'):
                                        return md
        return None
    except Exception:
        return None


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
                'owner': it.get('owner'),
                'kind': kind,
                'name': it.get('name'),
                'title': it.get('name'),  # For consistency with model
                'description': it.get('description', ''),
                'version': it.get('version', ''),
                'tags': it.get('tags', []),
                'file_count': it.get('file_count'),
                'line_count': it.get('line_count'),
                'manifest_data': it,
                'repository_url': repo.get('html_url'),
                'source': 'github',
            }
        )
    return out


def create_blueprint_from_manifest(manifest_data: Dict[str, Any], source_repo: Optional[Dict[str, Any]] = None) -> Blueprint:
    """Create a Blueprint instance from manifest data."""
    name = manifest_data.get('name', '').replace(' ', '_').lower()
    if not name:
        name = f"blueprint_{int(time.time())}"
    
    # Ensure unique name
    original_name = name
    counter = 1
    while Blueprint.objects.filter(name=name).exists():
        name = f"{original_name}_{counter}"
        counter += 1
    
    return Blueprint.objects.create(
        name=name,
        title=manifest_data.get('name', name),
        description=manifest_data.get('description', ''),
        version=manifest_data.get('version', '1.0.0'),
        tags=','.join(manifest_data.get('tags', [])),
        repository_url=source_repo.get('html_url') if source_repo else '' if source_repo else '',
        manifest_data=manifest_data,
        code_template=manifest_data.get('code_template', ''),
        required_mcp_servers=manifest_data.get('required_mcp_servers', []),
        category=manifest_data.get('category', 'ai_assistants'),
    )


def create_mcp_config_from_manifest(manifest_data: Dict[str, Any], source_repo: Optional[Dict[str, Any]] = None) -> MCPConfig:
    """Create an MCPConfig instance from manifest data."""
    name = manifest_data.get('name', '').replace(' ', '_').lower()
    if not name:
        name = f"mcp_config_{int(time.time())}"
    
    # Ensure unique name
    original_name = name
    counter = 1
    while MCPConfig.objects.filter(name=name).exists():
        name = f"{original_name}_{counter}"
        counter += 1
    
    return MCPConfig.objects.create(
        name=name,
        title=manifest_data.get('name', name),
        description=manifest_data.get('description', ''),
        version=manifest_data.get('version', '1.0.0'),
        tags=','.join(manifest_data.get('tags', [])),
        repository_url=source_repo.get('html_url') if source_repo else '',
        manifest_data=manifest_data,
        config_template=manifest_data.get('config_template', ''),
        server_name=manifest_data.get('server_name', ''),
    )


def sync_github_marketplace_items():
    """Synchronize GitHub marketplace items with local database."""
    # Get all configured topics and orgs
    topics = list(GITHUB_MARKETPLACE_TOPICS)
    orgs = list(GITHUB_MARKETPLACE_ORG_ALLOWLIST)
    
    # Search for repositories
    repos = search_repos_by_topics(topics, orgs, token=GITHUB_TOKEN)
    
    for repo in repos:
        # Fetch manifests from the repository
        manifests = fetch_repo_manifests(repo, token=GITHUB_TOKEN)
        
        # Process blueprints
        blueprint_manifests = [m for m in manifests if m.get('type') == 'blueprint' or m.get('kind') == 'blueprint']
        for manifest in blueprint_manifests:
            try:
                # Check if blueprint already exists
                name = manifest.get('name', '').replace(' ', '_').lower()
                if not name:
                    continue
                    
                # Update or create the blueprint
                blueprint, created = Blueprint.objects.get_or_create(
                    name=name,
                    defaults={
                        'title': manifest.get('name', name),
                        'description': manifest.get('description', ''),
                        'version': manifest.get('version', '1.0.0'),
                        'tags': ','.join(manifest.get('tags', [])),
                        'repository_url': repo.get('html_url'),
                        'manifest_data': manifest,
                        'code_template': manifest.get('code_template', ''),
                        'required_mcp_servers': manifest.get('required_mcp_servers', []),
                        'category': manifest.get('category', 'ai_assistants'),
                    }
                )
                
                if not created:
                    # Update existing blueprint
                    blueprint.title = manifest.get('name', name)
                    blueprint.description = manifest.get('description', '')
                    blueprint.version = manifest.get('version', '1.0.0')
                    blueprint.tags = ','.join(manifest.get('tags', []))
                    blueprint.repository_url = repo.get('html_url')
                    blueprint.manifest_data = manifest
                    blueprint.code_template = manifest.get('code_template', '')
                    blueprint.required_mcp_servers = manifest.get('required_mcp_servers', [])
                    blueprint.category = manifest.get('category', 'ai_assistants')
                    blueprint.save()
                    
            except Exception as e:
                print(f"Error processing blueprint manifest: {e}")
        
        # Process MCP configs
        mcp_manifests = [m for m in manifests if m.get('type') == 'mcp' or m.get('kind') == 'mcp']
        for manifest in mcp_manifests:
            try:
                # Check if MCP config already exists
                name = manifest.get('name', '').replace(' ', '_').lower()
                if not name:
                    continue
                    
                # Update or create the MCP config
                mcp_config, created = MCPConfig.objects.get_or_create(
                    name=name,
                    defaults={
                        'title': manifest.get('name', name),
                        'description': manifest.get('description', ''),
                        'version': manifest.get('version', '1.0.0'),
                        'tags': ','.join(manifest.get('tags', [])),
                        'repository_url': repo.get('html_url'),
                        'manifest_data': manifest,
                        'config_template': manifest.get('config_template', ''),
                        'server_name': manifest.get('server_name', ''),
                    }
                )
                
                if not created:
                    # Update existing MCP config
                    mcp_config.title = manifest.get('name', name)
                    mcp_config.description = manifest.get('description', '')
                    mcp_config.version = manifest.get('version', '1.0.0')
                    mcp_config.tags = ','.join(manifest.get('tags', []))
                    mcp_config.repository_url = repo.get('html_url')
                    mcp_config.manifest_data = manifest
                    mcp_config.config_template = manifest.get('config_template', '')
                    mcp_config.server_name = manifest.get('server_name', '')
                    mcp_config.save()
                    
            except Exception as e:
                print(f"Error processing MCP config manifest: {e}")


def get_filtered_marketplace_items(
    item_type: str,
    search: str = '',
    tag: str = '',
    sort: str = 'created_at',
    order: str = 'desc',
) -> List[Dict[str, Any]]:
    """Get filtered marketplace items based on various criteria."""
    if item_type == 'blueprint':
        queryset = Blueprint.objects.filter(is_active=True)
    elif item_type == 'mcp_config':
        queryset = MCPConfig.objects.filter(is_active=True)
    else:
        return []
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            models.Q(title__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(name__icontains=search)
        )
    
    # Apply tag filter
    if tag:
        queryset = queryset.filter(tags__icontains=tag)
    
    # Apply ordering
    order_field = sort
    if order == 'desc':
        order_field = f"-{sort}"
    
    queryset = queryset.order_by(order_field)
    
    # Convert to dictionary format
    items = []
    for item in queryset:
        item_dict = {
            'id': item.id,
            'name': item.name,
            'title': item.title,
            'description': item.description,
            'version': item.version,
            'tags': item.tag_list,
            'created_at': item.created_at.isoformat() if item.created_at else None,
            'updated_at': item.updated_at.isoformat() if item.updated_at else None,
            'repository_url': item.repository_url,
            'source': item.source,
            'manifest_data': item.manifest_data,
        }
        
        if item_type == 'blueprint':
            item_dict['required_mcp_servers'] = item.required_mcp_servers
            item_dict['category'] = item.category
        elif item_type == 'mcp_config':
            item_dict['server_name'] = item.server_name
            
        items.append(item_dict)
    
    return items