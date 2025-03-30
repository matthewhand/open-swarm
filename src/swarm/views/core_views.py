"""
Core/UI related views for the Swarm framework.
"""
import os
import json
import logging
from pathlib import Path

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm # Use standard auth form


# Assuming blueprint discovery happens elsewhere and results are available if needed
# from .utils import blueprints_metadata # Or however metadata is accessed

# Use the current config loader
from swarm.extensions.config.config_loader import load_config, find_config_file, DEFAULT_CONFIG_FILENAME

logger = logging.getLogger(__name__)

# --- Web UI Views (if ENABLE_WEBUI is True) ---

def index(request):
    """Render the main index page (likely the chat UI)."""
    # This view might need context data like available models/blueprints
    # It should only be active if ENABLE_WEBUI is true (checked in urls.py)
    logger.debug(f"Index view called for user: {request.user}")
    context = {
        'title': settings.SWARM_TITLE or "Open Swarm",
        'description': settings.SWARM_DESCRIPTION or "A Swarm Framework Interface",
        # Add other context needed by the template
    }
    # Ensure the template exists
    template_name = "swarm/index.html"
    # Check if template exists? Django handles TemplateDoesNotExist.
    return render(request, template_name, context)

def custom_login(request):
    """Handles user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                logger.info(f"User '{username}' logged in successfully.")
                return redirect('/') # Redirect to index after login
            else:
                logger.warning(f"Login failed for user '{username}': Invalid credentials.")
                # Return form with error (AuthenticationForm handles this)
        else:
            logger.warning(f"Login form invalid: {form.errors.as_json()}")
    else:
        form = AuthenticationForm()

    # Only render if ENABLE_WEBUI is true (checked in urls.py)
    return render(request, 'swarm/login.html', {'form': form})


def serve_swarm_config(request):
    """Serves the swarm_config.json content."""
    # Find the config file used by the blueprint base or config loader
    # This logic might need refinement depending on where config is reliably found
    config_path = None
    try:
         # Use the same logic as BlueprintBase if possible, or find_config_file
         config_path = find_config_file(filename=DEFAULT_CONFIG_FILENAME, start_dir=Path(settings.BASE_DIR).parent) # Search from project root
         if not config_path:
              # Fallback to location relative to settings? Unlikely to be correct.
              config_path = Path(settings.BASE_DIR) / '..' / DEFAULT_CONFIG_FILENAME # Adjust relative path if needed
              config_path = config_path.resolve()

         if config_path and config_path.exists():
              logger.info(f"Serving config from: {config_path}")
              # Load config to potentially redact sensitive info before serving
              config_data = load_config(config_path)
              # Redact sensitive keys (e.g., api_key)
              if 'llm' in config_data:
                   for profile in config_data['llm']: config_data['llm'][profile].pop('api_key', None)
              return JsonResponse(config_data)
         else:
              logger.error(f"Swarm config file not found at expected locations (tried: {config_path})")
              return JsonResponse({"error": "Configuration file not found."}, status=404)

    except Exception as e:
        logger.error(f"Error serving swarm config: {e}", exc_info=True)
        return JsonResponse({"error": "Failed to load or serve configuration."}, status=500)

# --- Potentially other core API views if needed ---
# Example: A view to list available blueprints (might duplicate CLI list command logic)

@csrf_exempt # If POST is needed and no CSRF token available from UI
def list_available_blueprints_api(request):
     """API endpoint to list discoverable blueprints."""
     # Re-use discovery logic if possible, or adapt from CLI
     from swarm.extensions.blueprint.discovery import discover_blueprints # Assuming this exists
     try:
        bp_dir = Path(settings.BLUEPRINTS_DIR) # Assuming settings has BLUEPRINTS_DIR
        discovered = discover_blueprints(directories=[str(bp_dir)])
        # Format the response
        blueprint_list = [{"name": name, "description": meta.get("description", "N/A")} for name, meta in discovered.items()]
        return JsonResponse({"blueprints": blueprint_list})
     except Exception as e:
          logger.error(f"Error listing blueprints via API: {e}", exc_info=True)
          return JsonResponse({"error": "Failed to list blueprints."}, status=500)


