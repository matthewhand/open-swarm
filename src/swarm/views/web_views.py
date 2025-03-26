"""
Web UI views for Open Swarm MCP Core.
Handles rendering index, blueprint pages, login, and serving config.
"""
import os
import json
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from swarm.utils.logger_setup import setup_logger
# Import the function to discover blueprints dynamically
from swarm.extensions.blueprint.blueprint_discovery import discover_blueprints
# Import the setting for the blueprints directory
from swarm.settings import BLUEPRINTS_DIR
# Import config loader if needed, or assume config is loaded elsewhere
from swarm.extensions.config.config_loader import load_server_config

logger = setup_logger(__name__)

@csrf_exempt
def index(request):
    """Render the main index page with dynamically discovered blueprint options."""
    logger.debug("Rendering index page")
    try:
        # Discover blueprints dynamically each time the index is loaded
        # Consider caching this if performance becomes an issue
        discovered_metadata = discover_blueprints(directories=[BLUEPRINTS_DIR])
        blueprint_names = list(discovered_metadata.keys())
        logger.debug(f"Rendering index with blueprints: {blueprint_names}")
    except Exception as e:
        logger.error(f"Error discovering blueprints for index page: {e}", exc_info=True)
        blueprint_names = [] # Show empty list on error

    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "enable_admin": os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t"),
        "blueprints": blueprint_names # Use the dynamically discovered list
    }
    return render(request, "index.html", context)

@csrf_exempt
def blueprint_webpage(request, blueprint_name):
    """Render a simple webpage for querying agents of a specific blueprint."""
    logger.debug(f"Received request for blueprint webpage: '{blueprint_name}'")
    try:
        # Discover blueprints to check if the requested one exists
        discovered_metadata = discover_blueprints(directories=[BLUEPRINTS_DIR])
        if blueprint_name not in discovered_metadata:
            logger.warning(f"Blueprint '{blueprint_name}' not found during discovery.")
            available_blueprints = "".join(f"<li>{bp}</li>" for bp in discovered_metadata.keys())
            return HttpResponse(
                f"<h1>Blueprint '{blueprint_name}' not found.</h1><p>Available blueprints:</p><ul>{available_blueprints}</ul>",
                status=404,
            )
        # Blueprint exists, render the page
        context = {
            "blueprint_name": blueprint_name,
            "dark_mode": request.session.get('dark_mode', True),
            "is_chatbot": False # Adjust if needed based on blueprint type
            }
        return render(request, "simple_blueprint_page.html", context)
    except Exception as e:
        logger.error(f"Error processing blueprint page for '{blueprint_name}': {e}", exc_info=True)
        return HttpResponse("<h1>Error loading blueprint page.</h1>", status=500)


@csrf_exempt
def custom_login(request):
    """Handle custom login at /accounts/login/, redirecting to 'next' URL on success."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # User authenticated successfully
            login(request, user)
            next_url = request.GET.get("next", "/chatbot/") # Default redirect
            logger.info(f"User '{username}' logged in successfully. Redirecting to '{next_url}'.")
            return redirect(next_url)
        else:
            # Authentication failed
            logger.warning(f"Failed login attempt for user '{username}'.")
            # Check if auto-login for 'testuser' is enabled (ONLY for development/testing)
            enable_auth = os.getenv("ENABLE_API_AUTH", "true").lower() in ("true", "1", "t") # Default to TRUE
            if not enable_auth:
                logger.info("API Auth is disabled. Attempting auto-login for 'testuser'.")
                try:
                    # Attempt to log in 'testuser' with a known password (e.g., 'testpass')
                    # Ensure this user/password exists in your DB or fixture
                    test_user = authenticate(request, username="testuser", password="testpass")
                    if test_user is not None:
                        login(request, test_user)
                        next_url = request.GET.get("next", "/chatbot/")
                        logger.info("Auto-logged in as 'testuser' because API auth is disabled. Redirecting.")
                        return redirect(next_url)
                    else:
                         logger.warning("Auto-login for 'testuser' failed (user/password incorrect or user doesn't exist).")
                except Exception as auto_login_err:
                     logger.error(f"Error during 'testuser' auto-login attempt: {auto_login_err}")

            # If authentication failed and auto-login didn't happen/failed
            return render(request, "account/login.html", {"error": "Invalid username or password."})

    # If GET request, just render the login form
    return render(request, "account/login.html")

# Default config structure to return if the actual file is missing/invalid
DEFAULT_CONFIG = {
    "llm": {
        "default": {
            "provider": "openai",
            "model": "gpt-4o", # More modern default
            "base_url": "https://api.openai.com/v1", # Standard OpenAI endpoint
            "api_key": "", # API key should usually come from env vars
            "temperature": 0.7
        }
    },
    "mcpServers": {},
    "blueprints": {}
}

@csrf_exempt # Usually not needed for GET, but doesn't hurt
def serve_swarm_config(request):
    """Serve the main swarm configuration file (swarm_config.json) as JSON."""
    # Construct path relative to Django settings.BASE_DIR
    config_path = Path(settings.BASE_DIR) / "swarm_config.json"
    logger.debug(f"Attempting to serve swarm config from: {config_path}")
    try:
        # Use Path object's read_text method for cleaner file reading
        config_content = config_path.read_text(encoding='utf-8')
        config_data = json.loads(config_content)
        logger.debug("Successfully loaded and parsed swarm_config.json")
        return JsonResponse(config_data)
    except FileNotFoundError:
        logger.error(f"Configuration file swarm_config.json not found at {config_path}. Serving default config.")
        return JsonResponse(DEFAULT_CONFIG, status=404) # Return 404 maybe? Or just default?
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {config_path}: {e}")
        # Return an error response instead of default config on parse error
        return JsonResponse({"error": f"Invalid JSON format in configuration file: {e}"}, status=500)
    except Exception as e:
         logger.error(f"Unexpected error serving swarm config: {e}", exc_info=True)
         return JsonResponse({"error": "An unexpected error occurred."}, status=500)
