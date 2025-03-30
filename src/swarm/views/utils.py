import logging
import redis
import json
import os
from functools import lru_cache
from typing import Dict, Type, Optional, Any

from django.conf import settings
from django.core.cache import cache # Using Django cache abstraction

# Assuming BlueprintBase is correctly located now
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.extensions.blueprint.blueprint_discovery import discover_blueprints, BlueprintLoadError
from swarm.extensions.config.config_loader import load_config

logger = logging.getLogger(__name__)

# --- Configuration and Blueprint Caching ---

# Keep these sync as they are simple lookups/loads
@lru_cache(maxsize=1)
def get_server_config() -> Dict[str, Any]:
    """Loads server configuration from the path specified in settings."""
    config_path = settings.SWARM_CONFIG_PATH
    logger.info(f"Loading server config from {config_path}")
    try:
        config = load_config(config_path)
        logger.info(f"Server config loaded successfully from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}. Returning empty config.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from configuration file {config_path}. Returning empty config.")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occurred loading config from {config_path}: {e}", exc_info=True)
        return {}

@lru_cache(maxsize=1)
def get_llm_profile(profile_name: str = "default") -> Optional[Dict[str, Any]]:
    """Gets a specific LLM profile from the server configuration."""
    config = get_server_config()
    profile = config.get("llm_profiles", {}).get(profile_name)
    if not profile:
        logger.warning(f"LLM profile '{profile_name}' not found in config.")
    return profile

@lru_cache(maxsize=1)
def get_available_blueprints() -> Dict[str, Type[BlueprintBase]]:
    """
    Discovers and returns available blueprints, caching the result.
    Uses Django cache for potential future invalidation needs.
    """
    cache_key = "available_blueprints"
    cached_blueprints = cache.get(cache_key)
    if cached_blueprints is not None:
        logger.debug("Returning cached blueprints.")
        return cached_blueprints

    logger.info(f"Discovering blueprints in: {settings.BLUEPRINT_DIRECTORY}")
    try:
        blueprints = discover_blueprints(settings.BLUEPRINT_DIRECTORY)
        logger.info(f"Discovered blueprints: {list(blueprints.keys())}")
        cache.set(cache_key, blueprints, timeout=None)
        return blueprints
    except Exception as e:
        logger.error(f"Error during blueprint discovery: {e}", exc_info=True)
        return {}

# --- Redis Connection (Keep sync for now) ---

@lru_cache(maxsize=1)
def get_redis_connection() -> Optional[redis.Redis]:
    """Establishes and returns a Redis connection, caching the connection object."""
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
        )
        r.ping()
        logger.info(f"Redis connection successful ({settings.REDIS_HOST}:{settings.REDIS_PORT}).")
        return r
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection failed ({settings.REDIS_HOST}:{settings.REDIS_PORT}): {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred connecting to Redis: {e}", exc_info=True)
        return None


# --- Blueprint Instantiation (Now Async) ---

# *** MADE ASYNC ***
async def get_blueprint_instance(blueprint_name: str, params: Optional[Dict[str, Any]] = None) -> Optional[BlueprintBase]:
    """
    Gets an instance of a specific blueprint by name. (Async version)
    """
    # Getting available blueprints is still sync and cached
    available_blueprints = get_available_blueprints()
    blueprint_class = available_blueprints.get(blueprint_name)

    if not blueprint_class:
        logger.warning(f"Blueprint class '{blueprint_name}' not found in available blueprints.")
        return None

    try:
        # Instantiation itself is sync, no await needed here
        if params:
            logger.debug(f"Instantiating blueprint '{blueprint_name}' with params: {params}")
            instance = blueprint_class(**params)
        else:
            logger.debug(f"Instantiating blueprint '{blueprint_name}' with no params.")
            instance = blueprint_class()
        # Log success from the *real* function if it runs
        logger.info(f"Initialized blueprint '{blueprint_name}' with profile '{getattr(instance, 'profile_name', 'N/A')}'")
        return instance
    except TypeError as e:
        logger.error(f"Error instantiating blueprint '{blueprint_name}' (check __init__ params): {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error instantiating blueprint '{blueprint_name}': {e}", exc_info=True)
        return None


# --- Access Validation (Keep sync) ---

def validate_model_access(user, model_name: str) -> bool:
    """
    Checks if the user has access to the requested model (blueprint).
    """
    available_blueprints = get_available_blueprints()
    if model_name not in available_blueprints:
        logger.warning(f"Model '{model_name}' is not in the list of available blueprints.")
        return False
    # TODO: Implement real access control
    logger.debug(f"Access validated for user '{user}' to model '{model_name}' (placeholder logic).")
    return True

