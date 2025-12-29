import logging
import sys

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings

from swarm.blueprints.dynamic_team.blueprint_dynamic_team import DynamicTeamBlueprint

# Assuming the discovery functions are correctly located now
from swarm.core.blueprint_discovery import discover_blueprints
from swarm.core.paths import (
    ensure_swarm_directories_exist,
    get_user_blueprints_dir,
    get_user_config_dir_for_swarm,
)

logger = logging.getLogger(__name__)

# Bridge module aliasing between 'swarm' and 'src.swarm' imports so globals are shared
try:
    if __name__ == 'swarm.views.utils':
        sys.modules.setdefault('src.swarm.views.utils', sys.modules[__name__])
    elif __name__ == 'src.swarm.views.utils':
        sys.modules.setdefault('swarm.views.utils', sys.modules[__name__])
except Exception:
    pass

# --- Caching ---
_blueprint_meta_cache = None # Cache for the {name: class} mapping
_blueprint_instance_cache = {} # Simple instance cache for no-param blueprints
_dynamic_registry: dict[str, dict] = {}


def _dynamic_registry_path():
    ensure_swarm_directories_exist()
    return get_user_config_dir_for_swarm() / "teams.json"


def load_dynamic_registry() -> dict[str, dict]:
    global _dynamic_registry
    if _dynamic_registry:
        return _dynamic_registry
    try:
        path = _dynamic_registry_path()
        if path.exists():
            import json
            _dynamic_registry = json.loads(path.read_text(encoding="utf-8")) or {}
        else:
            _dynamic_registry = {}
    except Exception:
        _dynamic_registry = {}
    return _dynamic_registry


def save_dynamic_registry() -> None:
    try:
        path = _dynamic_registry_path()
        import json
        path.write_text(json.dumps(_dynamic_registry, indent=2), encoding="utf-8")
    except Exception:
        # Non-fatal in demo mode
        pass


def register_dynamic_team(team_id: str, description: str | None = None, llm_profile: str | None = None) -> None:
    """Registers a dynamic team in memory and persists to disk.

    team_id is both the human-facing team name/slug and the model id exposed via /v1/models.
    """
    reg = load_dynamic_registry()
    reg[team_id] = {
        "id": team_id,
        "description": description or "Dynamic team",
        "llm_profile": llm_profile or "default",
    }
    global _blueprint_meta_cache
    _blueprint_meta_cache = None  # Force rebuild on next access
    save_dynamic_registry()


def deregister_dynamic_team(team_id: str) -> bool:
    """Removes a dynamic team from the registry. Returns True if removed."""
    reg = load_dynamic_registry()
    if team_id in reg:
        reg.pop(team_id, None)
        global _blueprint_meta_cache
        _blueprint_meta_cache = None
        save_dynamic_registry()
        return True
    return False


def reset_dynamic_registry() -> None:
    """Clears all dynamic teams and persists an empty registry."""
    global _dynamic_registry, _blueprint_meta_cache
    _dynamic_registry = {}
    _blueprint_meta_cache = None
    save_dynamic_registry()

# --- Blueprint Metadata Loading ---
def _load_all_blueprint_metadata_sync():
    """Synchronous helper to perform blueprint discovery."""
    global _blueprint_meta_cache
    logger.info("Discovering blueprint classes (sync)...")

    # 1. Discover bundled blueprints
    blueprint_classes = discover_blueprints(settings.BLUEPRINT_DIRECTORY)

    # 2. Discover user-installed blueprints (if directory exists)
    user_dir = get_user_blueprints_dir()
    if user_dir.is_dir():
        logger.info(f"Scanning user blueprints at {user_dir}")
        user_blueprints = discover_blueprints(str(user_dir))
        # Merge, preferring user installed if name collision (or handle error)
        # For now, simple update
        blueprint_classes.update(user_blueprints)

    # 3. Merge dynamic teams as blueprints
    dyn = load_dynamic_registry()
    for team_id, meta in dyn.items():
        blueprint_classes[team_id] = {
            "class_type": DynamicTeamBlueprint,
            "metadata": {
                "name": team_id,
                "description": meta.get("description", "Dynamic team"),
                "abbreviation": None,
                "tags": ["team", "dynamic"],
            },
        }
    logger.info(f"Found blueprint classes: {list(blueprint_classes.keys())}")
    _blueprint_meta_cache = blueprint_classes
    return blueprint_classes

@sync_to_async
def get_available_blueprints():
     """Asynchronously retrieves available blueprint classes."""
     global _blueprint_meta_cache
     if _blueprint_meta_cache is None:
          _load_all_blueprint_metadata_sync()
     return _blueprint_meta_cache

# --- Blueprint Instance Loading ---
# Removed _load_blueprint_class_sync

async def get_blueprint_instance(blueprint_id: str, params: dict = None):
    """Asynchronously gets an instance of a specific blueprint."""
    logger.debug(f"Getting instance for blueprint: {blueprint_id} with params: {params}")
    (blueprint_id, tuple(sorted(params.items())) if isinstance(params, dict) else params)

    if params is None and blueprint_id in _blueprint_instance_cache:
         logger.debug(f"Returning cached instance for {blueprint_id}")
         return _blueprint_instance_cache[blueprint_id]

    available_blueprint_classes = await get_available_blueprints()

    if not isinstance(available_blueprint_classes, dict) or blueprint_id not in available_blueprint_classes:
        logger.error(f"Blueprint ID '{blueprint_id}' not found in available blueprint classes.")
        return None

    blueprint_info = available_blueprint_classes[blueprint_id]
    blueprint_class = blueprint_info['class_type']

    try:
        # *** Instantiate the class WITHOUT the params argument ***
        # If blueprints need params, they should handle it internally
        # or the base class __init__ needs to accept **kwargs.
        instance = blueprint_class(blueprint_id=blueprint_id)
        # If it's a dynamic team blueprint and llm_profile is specified in registry, set it
        try:
            reg = load_dynamic_registry()
            team_info = reg.get(blueprint_id)
            if team_info and team_info.get("llm_profile") and hasattr(instance, "llm_profile_name"):
                instance.llm_profile_name = team_info["llm_profile"]
        except Exception:
            pass
        logger.info(f"Successfully instantiated blueprint: {blueprint_id}")
        # Optionally pass params later if needed, e.g., instance.set_params(params) if such a method exists
        if hasattr(instance, 'set_params') and callable(instance.set_params):
             instance.set_params(params) # Example of setting params after init

        if params is None:
             _blueprint_instance_cache[blueprint_id] = instance
        return instance
    except Exception as e:
        # Catch potential TypeError during instantiation too
        logger.error(f"Failed to instantiate blueprint class '{blueprint_id}': {e}", exc_info=True)
        return None

# --- Model Access Validation ---
def validate_model_access(user, model_name):
     """Synchronous permission check."""
     logger.debug(f"Validating access for user '{user}' to model '{model_name}'...")
     try:
         available = async_to_sync(get_available_blueprints)()
         is_available = model_name in available
         logger.debug(f"Model '{model_name}' availability: {is_available}")
         return is_available
     except Exception as e:
         logger.error(f"Error checking model availability during validation: {e}", exc_info=True)
         return False
