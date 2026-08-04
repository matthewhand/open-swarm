import logging
import time

# *** Import async_to_sync ***
from asgiref.sync import async_to_sync
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.auth import api_permission_classes

# Shared request body for creating/updating a custom blueprint (documents the
# OpenAPI requestBody so MCP/codegen clients know what fields to send).
_custom_blueprint_request = inline_serializer(
    name="CustomBlueprintRequest",
    fields={
        "id": serializers.CharField(required=False, help_text="Blueprint id (or provide name)."),
        "name": serializers.CharField(required=False, help_text="Display name (id or name is required)."),
        "description": serializers.CharField(required=False, allow_blank=True),
        "category": serializers.CharField(required=False, help_text="Default: ai_assistants."),
        "tags": serializers.ListField(child=serializers.CharField(), required=False),
        "requirements": serializers.CharField(required=False, allow_blank=True),
        "code": serializers.CharField(required=False, allow_blank=True, help_text="Blueprint source."),
        "required_mcp_servers": serializers.ListField(child=serializers.CharField(), required=False),
        "env_vars": serializers.ListField(child=serializers.CharField(), required=False),
    },
)

from swarm.services import github_topics_service as gh_service
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


class ModelsListView(APIView):
    """
    API view to list available models (blueprints) compatible with OpenAI's /v1/models format.
    """
    # Respect ENABLE_API_AUTH (was hard-coded AllowAny — open discovery when locked down).
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, *_args, **_kwargs):
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
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, *_args, **_kwargs):
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
    # Mutating surface: require token/session when API auth is enabled.
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, *_args, **_kwargs):
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
            return not (category and category != str(item.get("category", "")).lower())

        filtered = [i for i in items if match(i)]
        return Response({"object": "list", "data": filtered}, status=status.HTTP_200_OK)

    @extend_schema(summary="Create a custom blueprint", request=_custom_blueprint_request)
    def post(self, request, *_args, **_kwargs):
        try:
            body = request.data or {}
            bp_id = (body.get("id") or body.get("name") or "").strip()
            if not bp_id:
                return Response({"error": "id or name required"}, status=status.HTTP_400_BAD_REQUEST)
            bp_id = bp_id.lower().replace(" ", "_")

            lib = get_user_blueprint_library()
            custom = lib.get("custom", [])
            existing_ids = {i.get("id") for i in custom}
            if bp_id in existing_ids:
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
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def _load(self, bp_id: str):
        lib = get_user_blueprint_library()
        items = lib.get("custom", [])
        if not items and _custom_blueprints_registry:
            items = list(_custom_blueprints_registry)
        for i in items:
            if i.get("id") == bp_id:
                return lib, items, i
        return lib, items, None

    def get(self, request, blueprint_id: str, *_args, **_kwargs):
        lib, items, item = self._load(blueprint_id)
        if not item:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(item, status=status.HTTP_200_OK)

    def delete(self, request, blueprint_id: str, *_args, **_kwargs):
        lib, items, item = self._load(blueprint_id)
        if not item:
            return Response(status=status.HTTP_204_NO_CONTENT)
        items = [i for i in items if i.get("id") != blueprint_id]
        lib["custom"] = items
        if not save_user_blueprint_library(lib):
            return Response({"error": "failed to persist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Keep in-memory fallback registry in sync (GET falls back when disk empty).
        try:
            _custom_blueprints_registry.clear()
            _custom_blueprints_registry.extend(items)
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Update a custom blueprint", request=_custom_blueprint_request)
    def patch(self, request, blueprint_id: str, *_args, **_kwargs):
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
            try:
                _custom_blueprints_registry.clear()
                _custom_blueprints_registry.extend(items)
            except Exception:
                pass
            return Response(item, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error updating custom blueprint")
            return Response({"error": "internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    put = patch


class MarketplaceGitHubBlueprintsView(APIView):
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, *_args, **_kwargs):
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
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, request, *_args, **_kwargs):
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


class BlueprintSourceView(APIView):
    """Read-only source of a blueprint's directory: file list + one file's content.

    GET /v1/blueprints/<id>/source[?file=<name>] -> {files, primary, selected, content}.
    Confined to the blueprint's own directory under BLUEPRINT_DIRECTORY (no traversal).
    """
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    _ALLOWED_SUFFIXES = (".py", ".md", ".json", ".txt", ".toml", ".yaml", ".yml", ".cfg")

    def get(self, request, blueprint_id, *_args, **_kwargs):
        from pathlib import Path

        from swarm.settings import BLUEPRINT_DIRECTORY

        base = Path(BLUEPRINT_DIRECTORY).resolve()
        bp_dir = (base / blueprint_id).resolve()
        if base not in bp_dir.parents or not bp_dir.is_dir():
            return Response({"error": "blueprint not found"}, status=status.HTTP_404_NOT_FOUND)

        files = sorted(
            p for p in bp_dir.iterdir()
            if p.is_file() and p.suffix in self._ALLOWED_SUFFIXES
        )
        if not files:
            return Response({"id": blueprint_id, "files": [], "primary": None, "selected": None, "content": ""})

        primary = next((p for p in files if p.name.startswith("blueprint_")), files[0])
        target = primary
        req_name = request.query_params.get("file")
        if req_name:
            cand = (bp_dir / req_name).resolve()
            if cand.is_file() and cand.parent == bp_dir and cand.suffix in self._ALLOWED_SUFFIXES:
                target = cand
        try:
            content = target.read_text(encoding="utf-8", errors="replace")[:200_000]
        except OSError:
            content = ""

        return Response({
            "id": blueprint_id,
            "files": [{"name": p.name, "path": p.name} for p in files],
            "primary": primary.name,
            "selected": target.name,
            "content": content,
        })


class CliAgentsView(APIView):
    """CLI-agent catalog + native (built-in) consensus capability, for the Builder UI.

    GET /v1/cli-agents/ -> {clis: [...], native_consensus: {cli: [flag,"{n}"]}}.
    """
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, _request, *_args, **_kwargs):
        from swarm.core import cli_catalog

        return Response({
            "clis": cli_catalog.catalog_names(),
            "native_consensus": cli_catalog.NATIVE_CONSENSUS,
            "catalog": {n: cli_catalog.catalog_entry(n) for n in cli_catalog.catalog_names()},
        })


class ConfigOptionsView(APIView):
    """Everything the Builder UI needs to configure the new decoupling features.

    GET /v1/config-options/ ->
      {
        skills:        [{name, description, assets}],
        inference: {
          traits:      ["intelligence","speed","cost"],
          cli_traits:  {cli: {trait: 0..1}},     # per-provider defaults
          model_traits:{model: {trait: 0..1}},   # per-model overrides
          model_flags: {cli: "<flag>"},          # how each CLI pins a model
        },
        tools: {
          capabilities: ["web_search","browser",...],
          mcp_catalog:  [{name, provides, command, args, needs_auth, env, note}],
        },
      }
    """
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, _request, *_args, **_kwargs):
        from swarm.core import cli_catalog, inference_profile, skills, tool_capabilities

        return Response({
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "assets": s.assets,
                    "instructions": s.instructions,
                }
                for s in skills.discover_skills().values()
            ],
            "inference": {
                "traits": list(inference_profile.TRAITS),
                "cli_traits": cli_catalog.CLI_TRAITS,
                "model_traits": cli_catalog.MODEL_TRAITS,
                "model_flags": cli_catalog.MODEL_FLAG,
            },
            "tools": {
                "capabilities": sorted(
                    {c for s in tool_capabilities.CATALOG for c in s.provides}
                ),
                "mcp_catalog": [
                    {
                        "name": s.name,
                        "provides": list(s.provides),
                        "command": s.command,
                        "args": list(s.args),
                        "needs_auth": s.needs_auth,
                        "auth_env": list(s.auth_env),
                        "note": s.note,
                    }
                    for s in tool_capabilities.CATALOG
                ],
            },
        })


class BlueprintToolsView(APIView):
    """Resolve a blueprint's abstract tool needs to concrete MCP providers.

    GET /v1/blueprints/<id>/tools -> for a blueprint declaring ``tool_requirements``
    in its metadata, returns the providers each capability resolves to (non-auth
    preferred, auto-provisioned from the catalog), so the decoupling is inspectable:
      {
        requirements: {capability: "mandatory"|"optional"},
        servers:      {name: {command, args, provides, ...}},  # what to launch
        satisfied:    {capability: server_name},
        missing_mandatory: [...], skipped_optional: [...], ok: bool,
      }
    """
    def get_permissions(self):
        return [perm() for perm in api_permission_classes()]

    def get(self, _request, blueprint_id: str, *_args, **_kwargs):
        from swarm.core import tool_capabilities
        from swarm.core.config_loader import find_config_file, load_config

        blueprints = async_to_sync(get_available_blueprints)()
        info = blueprints.get(blueprint_id) if isinstance(blueprints, dict) else None
        if info is None:
            return Response({"detail": f"Unknown blueprint '{blueprint_id}'."},
                            status=status.HTTP_404_NOT_FOUND)
        meta = info.get("metadata", {}) if isinstance(info, dict) else {}
        requirements = meta.get("tool_requirements") or {}

        cfg_file = find_config_file()
        config = load_config(cfg_file) if cfg_file else {}
        servers, res = tool_capabilities.resolve_mcp_servers(requirements, config)
        return Response({
            "blueprint": blueprint_id,
            "requirements": tool_capabilities.normalize_requirements(requirements),
            "servers": servers,
            "satisfied": res.satisfied,
            "missing_mandatory": res.missing_mandatory,
            "skipped_optional": res.skipped_optional,
            "ok": res.ok,
        })
