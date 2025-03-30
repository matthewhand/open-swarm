import logging
from django.conf import settings
from asgiref.sync import sync_to_async, async_to_sync

# Assuming the discovery functions are correctly located now
from swarm.extensions.blueprint.blueprint_discovery import discover_blueprints

logger = logging.getLogger(__name__)

# --- Caching ---
_blueprint_meta_cache = None # Cache for the {name: class} mapping
_blueprint_instance_cache = {} # Simple instance cache for no-param blueprints

# --- Blueprint Metadata Loading ---
def _load_all_blueprint_metadata_sync():
    """Synchronous helper to perform blueprint discovery."""
    global _blueprint_meta_cache
    logger.info("Discovering blueprint classes (sync)...")
    blueprint_classes = discover_blueprints(settings.BLUEPRINT_DIRECTORY)
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
    cache_key = (blueprint_id, tuple(sorted(params.items())) if isinstance(params, dict) else params)

    if params is None and blueprint_id in _blueprint_instance_cache:
         logger.debug(f"Returning cached instance for {blueprint_id}")
         return _blueprint_instance_cache[blueprint_id]

    available_blueprint_classes = await get_available_blueprints()

    if not isinstance(available_blueprint_classes, dict) or blueprint_id not in available_blueprint_classes:
        logger.error(f"Blueprint ID '{blueprint_id}' not found in available blueprint classes.")
        return None

    blueprint_class = available_blueprint_classes[blueprint_id]

    try:
        # *** Instantiate the class WITHOUT the params argument ***
        # If blueprints need params, they should handle it internally
        # or the base class __init__ needs to accept **kwargs.
        instance = blueprint_class()
        logger.info(f"Successfully instantiated blueprint: {blueprint_id}")
        # Optionally pass params later if needed, e.g., instance.set_params(params) if such a method exists
        if hasattr(instance, 'set_params') and callable(getattr(instance, 'set_params')):
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
