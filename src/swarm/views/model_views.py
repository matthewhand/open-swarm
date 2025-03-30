"""
Model listing views for Open Swarm MCP Core.
Dynamically discovers blueprints and lists them alongside configured LLMs.
"""
import os
import logging
from pathlib import Path
from django.http import JsonResponse
from django.conf import settings # Import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny # Import AllowAny
from drf_spectacular.utils import extend_schema

from swarm.utils.logger_setup import setup_logger
# Import the function to discover blueprints
from swarm.extensions.blueprint import discover_blueprints
# Import config loader correctly
from swarm.extensions.config.config_loader import load_config, find_config_file, DEFAULT_CONFIG_FILENAME

logger = setup_logger(__name__)

@extend_schema(
    summary="List Available Models",
    description="Provides a list of available models, including configured LLMs and discovered blueprints."
)
@api_view(['GET'])
@authentication_classes([]) # No auth needed for model listing? Adjust if required.
@permission_classes([AllowAny])
def list_models(request):
    """
    Lists available models compatible with the OpenAI API standard.
    Includes both configured LLMs and discovered blueprints.
    """
    data = []
    created_time = int(os.path.getmtime(__file__)) # Use file mod time as a proxy

    # --- Load Config ---
    # Need to load config here to get LLM profiles
    config = {}
    try:
        config_path_obj = find_config_file(start_dir=Path(settings.BASE_DIR).parent) # Use default filename search
        if config_path_obj:
             config = load_config(config_path_obj)
        else:
             logger.warning("list_models: Config file not found, only listing blueprints.")
             config = {"llm": {}, "agents": {}, "settings": {}}
    except Exception as e:
        logger.error(f"list_models: Error loading config: {e}", exc_info=True)
        config = {"llm": {}, "agents": {}, "settings": {}}


    # --- List Configured LLMs ---
    llm_profiles = config.get("llm", {})
    for model_id, profile in llm_profiles.items():
        if isinstance(profile, dict): # Ensure profile is a dict
             data.append({
                 "id": model_id,
                 "object": "model",
                 "created": created_time,
                 "owned_by": profile.get("provider", "unknown"), # Use provider as owner
                 "title": profile.get("title", model_id.replace('_', ' ').title()), # Nicer title
                 "description": profile.get("description", f"LLM profile: {model_id}")
             })
        else:
            logger.warning(f"Skipping invalid LLM profile entry: {model_id}")


    # --- List Discovered Blueprints ---
    # Re-discover or use cached metadata from utils? Using cached is faster.
    from swarm.views.utils import blueprints_metadata # Access cached metadata

    for blueprint_id, meta in blueprints_metadata.items():
        # Avoid listing duplicates if an LLM profile has the same name as a blueprint
        if not any(d['id'] == blueprint_id for d in data):
             data.append({
                 "id": blueprint_id,
                 "object": "model", # Treat blueprints as 'models' in this context
                 "created": meta.get("created_time", created_time), # Use metadata time if available
                 "owned_by": "swarm-blueprint",
                 # Use metadata for title/description if available
                 "title": meta.get("title", blueprint_id.replace('_', ' ').title()),
                 "description": meta.get("description", f"Swarm Blueprint: {blueprint_id}")
             })

    logger.info(f"Listed {len(data)} models (LLMs + Blueprints).")
    return JsonResponse({
        "object": "list",
        "data": data
    })

