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

# Assuming blueprint discovery happens elsewhere and results are available if needed
# from .utils import blueprints_metadata # Or however metadata is accessed
from swarm.extensions.config.config_loader import load_server_config # Import if needed

logger = logging.getLogger(__name__)

# Placeholder for blueprint metadata if needed by index
# In a real app, this might be loaded dynamically or passed via context
try:
    # Attempt to import the discovery function if views need dynamic data
    from swarm.extensions.blueprint.blueprint_discovery import discover_blueprints
    # Note: Calling discover_blueprints here might be too early or cause issues.
    # It's often better handled in specific views that need it (like list_models)
    # or passed via Django context processors.
    # For now, provide an empty dict as fallback.
    try:
        # Use settings.BLUEPRINTS_DIR which should be configured
        blueprints_metadata = discover_blueprints(directories=[str(settings.BLUEPRINTS_DIR)])
    except Exception:
        blueprints_metadata = {}
except ImportError:
    blueprints_metadata = {}


@csrf_exempt
def index(request):
    """Render the main index page with blueprint options."""
    logger.debug("Rendering index page")
    # Get blueprint names from the potentially loaded metadata
    blueprint_names_list = list(blueprints_metadata.keys())
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "enable_admin": os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t"),
        "blueprints": blueprint_names_list # Pass the list of names
    }
    return render(request, "index.html", context)

DEFAULT_CONFIG = {
    "llm": {
        "default": {
            "provider": "openai",
            "model": "gpt-4o", # Example fallback model
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "temperature": 0.3
        }
    },
     "blueprints": {},
     "mcpServers": {}
}

def serve_swarm_config(request):
    """Serve the swarm configuration file as JSON."""
    try:
        # Use load_server_config which handles finding the file
        config_data = load_server_config()
        return JsonResponse(config_data)
    except (FileNotFoundError, ValueError, Exception) as e:
        logger.error(f"Error serving swarm_config.json: {e}. Serving default.")
        # Return a default config on error
        return JsonResponse(DEFAULT_CONFIG, status=500)


@csrf_exempt
def custom_login(request):
    """Handle custom login at /accounts/login/, redirecting to 'next' URL on success."""
    from django.contrib.auth.models import User # Import here to avoid potential early init issues
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", getattr(settings, 'LOGIN_REDIRECT_URL', '/')) # Use setting or fallback
            logger.info(f"User '{username}' logged in successfully. Redirecting to {next_url}")
            return redirect(next_url)
        else:
            # If ENABLE_API_AUTH is false, auto-login as testuser (for dev/test convenience)
            enable_auth = os.getenv("ENABLE_API_AUTH", "true").lower() in ("true", "1", "t") # Default to TRUE
            if not enable_auth:
                try:
                    # Ensure test user exists and has a known password
                    user, created = User.objects.get_or_create(username="testuser")
                    if created or not user.has_usable_password():
                         user.set_password("testpass") # Set a default password
                         user.save()

                    if user.check_password("testpass"): # Check against the known password
                        login(request, user)
                        next_url = request.GET.get("next", getattr(settings, 'LOGIN_REDIRECT_URL', '/'))
                        logger.info(f"Auto-logged in as 'testuser' since ENABLE_API_AUTH is false")
                        return redirect(next_url)
                    else:
                         logger.warning("Auto-login failed: 'testuser' exists but password incorrect.")

                except Exception as auto_login_err:
                    logger.error(f"Error during testuser auto-login attempt: {auto_login_err}")
            # If authentication failed (and auto-login didn't happen or failed)
            logger.warning(f"Login failed for user '{username}'.")
            return render(request, "account/login.html", {"error": "Invalid credentials"})
    # If GET request
    return render(request, "account/login.html")

# Add any other views that were originally in the main views.py if needed
