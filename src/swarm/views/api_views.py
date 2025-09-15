import logging
import time

# *** Import async_to_sync ***
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.marketplace import github_service as gh_service
from swarm.settings import (
    ENABLE_GITHUB_MARKETPLACE,
    GITHUB_MARKETPLACE_ORG_ALLOWLIST,
    GITHUB_MARKETPLACE_TOPICS,
    GITHUB_TOKEN,
)
from swarm.views.blueprint_library_views import (
    get_user_blueprint_library,
    save_user_blueprint_library,
)
from swarm.views.utils import get_available_blueprints

logger = logging.getLogger(__name__)

# In-memory fallback registry used in tests to simulate persistence when
# get_user_blueprint_library/save_user_blueprint_library are monkeypatched.
_custom_blueprints_registry: list[dict] = []


# --- Optional: Marketplace (Wagtail) headless API helpers ---
def get_marketplace_blueprints() -> list[dict]:
    """Return blueprint marketplace items as plain dicts.

    Attempts to import Wagtail models. If unavailable or disabled, returns an empty list.
    """
    try:
        from django.conf import settings as dj_settings
        if not getattr(dj_settings, 'ENABLE_WAGTAIL', False):
            return []
        from swarm.marketplace.models import BlueprintPage  # type: ignore
        items = []
        # Late import to avoid hard dependency during tests
        for page in BlueprintPage.objects.live().public():  # type: ignore[attr-defined]
            cat = None
            try:
                if getattr(page, 'category', None):
                    cat = {
                        'slug': getattr(page.category, 'slug', None),
                        'name': getattr(page.category, 'name', None),
                    }
            except Exception:
                cat = None
            tags_str = getattr(page, 'tags', '') or ''
            tag_list = [t.strip() for t in str(tags_str).split(',') if t.strip()]
            items.append({
                'id': page.id,
                'title': getattr(page, 'title', None),
                'summary': getattr(page, 'summary', ''),
                'version': getattr(page, 'version', ''),
                'category': cat,
                'tags': tag_list,
                'repository_url': getattr(page, 'repository_url', ''),
                # Expose templates as content fields (already validated to avoid secrets)
                'manifest_json': getattr(page, 'manifest_json', ''),
                'code_template': getattr(page, 'code_template', ''),
            })
        return items
    except Exception:
        return []


def get_marketplace_mcp_configs() -> list[dict]:
    """Return MCP config marketplace items as plain dicts.

    Attempts to import Wagtail models. If unavailable or disabled, returns an empty list.
    """
    try:
        from django.conf import settings as dj_settings
        if not getattr(dj_settings, 'ENABLE_WAGTAIL', False):
            return []
        from swarm.marketplace.models import MCPConfigPage  # type: ignore
        items = []
        for page in MCPConfigPage.objects.live().public():  # type: ignore[attr-defined]
            items.append({
                'id': page.id,
                'title': getattr(page, 'title', None),
                'summary': getattr(page, 'summary', ''),
                'version': getattr(page, 'version', ''),
                'server_name': getattr(page, 'server_name', ''),
                'config_template': getattr(page, 'config_template', ''),
            })
        return items
    except Exception:
        return []

class ModelsListView(APIView):
    """
    API view to list available models (blueprints) compatible with OpenAI's /v1/models format.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            # *** Use async_to_sync to call the async function ***
            available_blueprints = async_to_sync(get_available_blueprints)()

            models_data = []
            current_time = int(time.time())
            if isinstance(available_blueprints, dict):
                blueprint_ids = available_blueprints.keys()
            elif isinstance(available_blueprints, list):
                 blueprint_ids = available_blueprints
            else:
                 logger.error(f"Unexpected type from get_available_blueprints: {type(available_blueprints)}")
                 blueprint_ids = []

            for blueprint_id in blueprint_ids:
                models_data.append({
                    "id": blueprint_id,
                    "object": "model",
                    "created": current_time,
                    "owned_by": "open-swarm",
                })

            response_payload = {
                "object": "list",
                "data": models_data,
            }
            return Response(response_payload, status=status.HTTP_200_OK)

        except Exception:
            logger.exception("Error retrieving available models.")
            return Response(
                {"error": "Failed to retrieve models list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BlueprintsListView(APIView):
    """
    API view to list available blueprints with richer metadata than /v1/models.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            available_blueprints = async_to_sync(get_available_blueprints)()
            data = []
            # Filters: search, required_mcp
            search = (request.query_params.get("search") or "").strip().lower()
            required_mcp = (request.query_params.get("required_mcp") or "").strip().lower()
            if isinstance(available_blueprints, dict):
                for blueprint_id, info in available_blueprints.items():
                    meta = info.get("metadata", {}) if isinstance(info, dict) else {}
                    name = meta.get("name", blueprint_id)
                    description = meta.get("description") or ""
                    req_mcps = [str(x).lower() for x in (meta.get("required_mcp_servers") or [])]

                    if search and not (
                        search in blueprint_id.lower()
                        or search in str(name).lower()
                        or search in str(description).lower()
                    ):
                        continue
                    if required_mcp and required_mcp not in req_mcps:
                        continue

                    data.append({
                        "id": blueprint_id,
                        "object": "blueprint",
                        "name": name,
                        "description": description,
                        "abbreviation": meta.get("abbreviation"),
                        "required_mcp_servers": meta.get("required_mcp_servers") or [],
                        # Placeholders for future enrichment
                        "tags": meta.get("tags") or [],
                        "installed": None,
                        "compiled": None,
                    })
            else:
                logger.error(f"Unexpected type from get_available_blueprints: {type(available_blueprints)}")

            response_payload = {
                "object": "list",
                "data": data,
            }
            return Response(response_payload, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error retrieving blueprints list.")
            return Response(
                {"error": "Failed to retrieve blueprints list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomBlueprintsView(APIView):
    """
    CRUD for user custom blueprints stored in blueprint_library.json.

    GET  /v1/blueprints/custom/           -> list (with optional filters)
    POST /v1/blueprints/custom/           -> create
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        lib = get_user_blueprint_library()
        items = lib.get("custom", [])
        if not items and _custom_blueprints_registry:
            items = list(_custom_blueprints_registry)

        # Simple filters: search, tag, category
        search = (request.query_params.get("search") or "").strip().lower()
        tag = (request.query_params.get("tag") or "").strip().lower()
        category = (request.query_params.get("category") or "").strip().lower()

        def match(item: dict) -> bool:
            if search and not (
                search in (item.get("id", "").lower())
                or search in (str(item.get("name", "")).lower())
                or search in (str(item.get("description", "")).lower())
            ):
                return False
            if tag:
                tags = [str(t).lower() for t in item.get("tags", [])]
                if tag not in tags:
                    return False
            if category and category != str(item.get("category", "")).lower():
                return False
            return True

        filtered = [i for i in items if match(i)]
        return Response({"object": "list", "data": filtered}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            body = request.data or {}
            bp_id = (body.get("id") or body.get("name") or "").strip()
            if not bp_id:
                return Response({"error": "id or name required"}, status=status.HTTP_400_BAD_REQUEST)
            bp_id = bp_id.lower().replace(" ", "_")

            lib = get_user_blueprint_library()
            custom = lib.get("custom", [])
            if any(i.get("id") == bp_id for i in custom):
                return Response({"error": "id already exists"}, status=status.HTTP_409_CONFLICT)

            item = {
                "id": bp_id,
                "name": body.get("name") or bp_id,
                "description": body.get("description") or "",
                "category": body.get("category") or "ai_assistants",
                "tags": body.get("tags") or [],
                "requirements": body.get("requirements") or "",
                "code": body.get("code") or "",
                # Optional metadata to help clients
                "required_mcp_servers": body.get("required_mcp_servers") or [],
                "env_vars": body.get("env_vars") or [],
            }
            custom.append(item)
            lib["custom"] = custom
            if not save_user_blueprint_library(lib):
                return Response({"error": "failed to persist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Update fallback registry for test environments
            try:
                _custom_blueprints_registry.clear()
                _custom_blueprints_registry.extend(custom)
            except Exception:
                pass
            return Response(item, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Error creating custom blueprint")
            return Response({"error": "internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomBlueprintDetailView(APIView):
    """
    GET    /v1/blueprints/custom/<id>/
    PATCH  /v1/blueprints/custom/<id>/
    PUT    /v1/blueprints/custom/<id>/
    DELETE /v1/blueprints/custom/<id>/
    """
    permission_classes = [AllowAny]

    def _load(self, bp_id: str):
        lib = get_user_blueprint_library()
        items = lib.get("custom", [])
        if not items and _custom_blueprints_registry:
            items = list(_custom_blueprints_registry)
        for i in items:
            if i.get("id") == bp_id:
                return lib, items, i
        return lib, items, None

    def get(self, request, blueprint_id: str, *args, **kwargs):
        lib, items, item = self._load(blueprint_id)
        if not item:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(item, status=status.HTTP_200_OK)

    def delete(self, request, blueprint_id: str, *args, **kwargs):
        lib, items, item = self._load(blueprint_id)
        if not item:
            return Response(status=status.HTTP_204_NO_CONTENT)
        items = [i for i in items if i.get("id") != blueprint_id]
        lib["custom"] = items
        if not save_user_blueprint_library(lib):
            return Response({"error": "failed to persist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, blueprint_id: str, *args, **kwargs):
        try:
            lib, items, item = self._load(blueprint_id)
            if not item:
                return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
            body = request.data or {}
            for key in [
                "name",
                "description",
                "category",
                "tags",
                "requirements",
                "code",
                "required_mcp_servers",
                "env_vars",
            ]:
                if key in body:
                    item[key] = body[key]
            if not save_user_blueprint_library(lib):
                return Response({"error": "failed to persist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(item, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error updating custom blueprint")
            return Response({"error": "internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    put = patch


class MarketplaceBlueprintsView(APIView):
    """Headless API for marketplace blueprint pages (optional Wagtail)."""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        items = get_marketplace_blueprints()
        # Simple filters: search by title or tag
        search = (request.query_params.get('search') or '').strip().lower()
        tag = (request.query_params.get('tag') or '').strip().lower()

        def match(it: dict) -> bool:
            if search and not (
                search in str(it.get('title', '')).lower()
                or search in str(it.get('summary', '')).lower()
            ):
                return False
            if tag:
                tags = [str(t).lower() for t in it.get('tags', [])]
                if tag not in tags:
                    return False
            return True

        data = [it for it in items if match(it)]
        return Response({'object': 'list', 'data': data}, status=status.HTTP_200_OK)


class MarketplaceMCPConfigsView(APIView):
    """Headless API for marketplace MCP config pages (optional Wagtail)."""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        items = get_marketplace_mcp_configs()
        # Simple filters: search by title or server_name
        search = (request.query_params.get('search') or '').strip().lower()
        server = (request.query_params.get('server') or '').strip().lower()

        def match(it: dict) -> bool:
            if search and not (
                search in str(it.get('title', '')).lower()
                or search in str(it.get('summary', '')).lower()
            ):
                return False
            if server and server not in str(it.get('server_name', '')).lower():
                return False
            return True

        data = [it for it in items if match(it)]
        return Response({'object': 'list', 'data': data}, status=status.HTTP_200_OK)


class MarketplaceGitHubBlueprintsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not ENABLE_GITHUB_MARKETPLACE:
            return Response({'object': 'list', 'data': []}, status=status.HTTP_200_OK)
        search = (request.query_params.get('search') or '').strip()
        org = (request.query_params.get('org') or '').strip()
        topic = (request.query_params.get('topic') or '').strip()
        sort = (request.query_params.get('sort') or 'stars').strip()
        order = (request.query_params.get('order') or 'desc').strip()
        topics = list(GITHUB_MARKETPLACE_TOPICS)
        if topic:
            topics = [topic]
        orgs = list(GITHUB_MARKETPLACE_ORG_ALLOWLIST)
        if org:
            orgs = [org]

        repos = gh_service.search_repos_by_topics(topics, orgs, sort=(None if sort == 'last_used' else sort), order=order, query=search, token=GITHUB_TOKEN)
        items: list[dict] = []
        for repo in repos:
            manifests = gh_service.fetch_repo_manifests(repo, token=GITHUB_TOKEN)
            items.extend(gh_service.to_marketplace_items(repo, manifests, kind='blueprint'))
        if sort == 'last_used':
            usage = get_last_used_map()
            def score(it: dict) -> float:
                key = (it.get('repo_full_name'), it.get('name'))
                return usage.get(key, 0.0)
            items.sort(key=score, reverse=(order != 'asc'))
        return Response({'object': 'list', 'data': items}, status=status.HTTP_200_OK)


class MarketplaceGitHubMCPConfigsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if not ENABLE_GITHUB_MARKETPLACE:
            return Response({'object': 'list', 'data': []}, status=status.HTTP_200_OK)
        search = (request.query_params.get('search') or '').strip()
        org = (request.query_params.get('org') or '').strip()
        topic = (request.query_params.get('topic') or '').strip()
        sort = (request.query_params.get('sort') or 'stars').strip()
        order = (request.query_params.get('order') or 'desc').strip()
        topics = list(GITHUB_MARKETPLACE_TOPICS)
        if topic:
            topics = [topic]
        orgs = list(GITHUB_MARKETPLACE_ORG_ALLOWLIST)
        if org:
            orgs = [org]

        repos = gh_service.search_repos_by_topics(topics, orgs, sort=(None if sort == 'last_used' else sort), order=order, query=search, token=GITHUB_TOKEN)
        items: list[dict] = []
        for repo in repos:
            manifests = gh_service.fetch_repo_manifests(repo, token=GITHUB_TOKEN)
            items.extend(gh_service.to_marketplace_items(repo, manifests, kind='mcp'))
        if sort == 'last_used':
            usage = get_last_used_map()
            def score(it: dict) -> float:
                key = (it.get('repo_full_name'), it.get('name'))
                return usage.get(key, 0.0)
            items.sort(key=score, reverse=(order != 'asc'))
        return Response({'object': 'list', 'data': items}, status=status.HTTP_200_OK)


def get_last_used_map() -> dict[tuple[str, str], float]:
    """Return mapping of (repo_full_name, item_name) -> last_used timestamp.

    Placeholder for now: returns empty dict. A future implementation will pull
    per-user usage from the database. Tests monkeypatch this function.
    """
    return {}
