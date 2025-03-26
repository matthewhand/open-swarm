"""
Model listing views for Open Swarm MCP Core.
Dynamically discovers blueprints and lists them alongside configured LLMs.
"""
import os
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny # Import AllowAny
from drf_spectacular.utils import extend_schema

from swarm.utils.logger_setup import setup_logger
# Import the function to discover blueprints, not the metadata variable
from swarm.extensions.blueprint.blueprint_discovery import discover_blueprints
# Import utility to filter blueprints if needed
from swarm.extensions.blueprint.blueprint_utils import filter_blueprints
# Import config loader or access config globally if set up
# Using utils seems less direct, let's assume config needs loading or is globally available
# from swarm.views.utils import config # This import might be problematic, load directly if needed
from swarm.extensions.config.config_loader import load_server_config
from swarm.settings import BLUEPRINTS_DIR # Import the directory setting

logger = setup_logger(__name__)

@extend_schema(
    responses={
        200: {
            "type": "object",
            "properties": {
                "object": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "object": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        }
    },
    summary="Lists LLMs, config-defined blueprints, and discovered blueprints as models."
)
@api_view(["GET"])
@permission_classes([AllowAny]) # Use AllowAny directly
@authentication_classes([]) # No authentication required for listing models
def list_models(request):
    """List available LLMs, config-defined blueprints, and discovered blueprints."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed. Use GET."}, status=405)

    try:
        # Load configuration each time or ensure it's loaded globally/cached
        config = load_server_config() # Load config to get LLMs and config blueprints

        # 1. LLMs from config (marked as passthrough)
        llm_config = config.get("llm", {})
        llm_data = [
            {
                "id": key,
                "object": "llm", # Mark as llm type
                "title": conf.get("model", key), # Use model name or key as title
                "description": f"Provider: {conf.get('provider', 'N/A')}, Model: {conf.get('model', 'N/A')}"
            }
            for key, conf in llm_config.items() if conf.get("passthrough")
        ]

        # 2. Blueprints defined directly in swarm_config.json
        config_blueprints = config.get("blueprints", {})
        config_bp_data = [
            {
                "id": key,
                "object": "blueprint", # Mark as blueprint type
                "title": bp.get("title", key),
                "description": bp.get("description", f"Blueprint '{key}' from configuration file.")
            }
            for key, bp in config_blueprints.items()
        ]

        # 3. Dynamically discovered blueprints from the blueprints directory
        # Ensure BLUEPRINTS_DIR is correctly pointing to your blueprints location relative to project root
        try:
            # Call discover_blueprints function to get the metadata dictionary
            discovered_blueprints_metadata = discover_blueprints(directories=[BLUEPRINTS_DIR])
        except FileNotFoundError:
             logger.warning(f"Blueprints directory '{BLUEPRINTS_DIR}' not found. No blueprints discovered dynamically.")
             discovered_blueprints_metadata = {}
        except Exception as discover_err:
             logger.error(f"Error discovering blueprints: {discover_err}", exc_info=True)
             discovered_blueprints_metadata = {}


        # Filter discovered blueprints based on environment variable if set
        allowed_blueprints_str = os.getenv("SWARM_BLUEPRINTS")
        if allowed_blueprints_str and allowed_blueprints_str.strip():
            # Use the imported filter_blueprints utility
            final_discovered_metadata = filter_blueprints(discovered_blueprints_metadata, allowed_blueprints_str)
            logger.info(f"Filtering discovered blueprints based on SWARM_BLUEPRINTS env var. Kept: {list(final_discovered_metadata.keys())}")
        else:
            final_discovered_metadata = discovered_blueprints_metadata # Use all discovered if no filter

        # Format discovered blueprint data
        discovered_bp_data = [
            {
                "id": key,
                "object": "blueprint", # Mark as blueprint type
                "title": meta.get("title", key),
                "description": meta.get("description", f"Discovered blueprint '{key}'.")
            }
            for key, meta in final_discovered_metadata.items()
        ]

        # 4. Merge all data sources
        # Start with LLMs and config blueprints
        merged_data = llm_data + config_bp_data
        # Keep track of IDs already added
        seen_ids = {item["id"] for item in merged_data}
        # Add discovered blueprints only if their ID hasn't been used by config/LLMs
        for bp_item in discovered_bp_data:
            if bp_item["id"] not in seen_ids:
                merged_data.append(bp_item)
                seen_ids.add(bp_item["id"]) # Mark ID as seen

        logger.debug(f"Returning {len(merged_data)} models (LLMs + Blueprints).")
        # Return the merged list in the expected OpenAI-like format
        return JsonResponse({"object": "list", "data": merged_data}, status=200)

    except Exception as e:
        # Catch-all for unexpected errors during the process
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JsonResponse({"error": "Internal Server Error while listing models."}, status=500)

