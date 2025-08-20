"""
Web UI views for Open Swarm MCP Core.
Handles rendering index, blueprint pages, login, and serving config.
"""
import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

# Import config loader if needed, or assume config is loaded elsewhere
# Import the function to discover blueprints dynamically
from swarm.core.blueprint_discovery import discover_blueprints

# Import the setting for the blueprints directory
from swarm.settings import BLUEPRINT_DIRECTORY
from swarm.utils.logger_setup import setup_logger
from .utils import load_dynamic_registry, register_dynamic_team, deregister_dynamic_team, reset_dynamic_registry
from swarm.core.paths import get_user_config_dir_for_swarm

logger = setup_logger(__name__)

@csrf_exempt
def index(request):
    """Render the main index page with dynamically discovered blueprint options."""
    logger.debug("Rendering index page")
    try:
        # Discover blueprints dynamically each time the index is loaded
        # Consider caching this if performance becomes an issue
        discovered_metadata = discover_blueprints(directories=[BLUEPRINT_DIRECTORY])
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
        discovered_metadata = discover_blueprints(directories=[BLUEPRINT_DIRECTORY])
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


def _webui_enabled() -> bool:
    return os.getenv("ENABLE_WEBUI", "false").lower() in ("true", "1", "t", "yes", "y")


@csrf_exempt
def team_launcher(request):
    """
    Render a minimal Team Launcher UI that allows selecting a blueprint (team),
    entering an instruction, and launching via /v1/chat/completions with stream=true.
    Gated behind ENABLE_WEBUI.
    """
    if not _webui_enabled():
        return HttpResponse("Web UI disabled. Set ENABLE_WEBUI=true to enable.", status=404)

    context = {
        "api_auth_enabled": bool(os.getenv("API_AUTH_TOKEN")),
        **_profiles_ctx(),
    }
    return render(request, "teams_launch.html", context)


@csrf_exempt
def team_admin(request):
    """Simple admin page to list and add dynamic teams."""
    if not _webui_enabled():
        return HttpResponse("Web UI disabled. Set ENABLE_WEBUI=true to enable.", status=404)

    if request.method == "POST":
        action = (request.POST.get("action") or "add").lower()
        if action == "delete":
            team_id = (request.POST.get("team_id") or "").strip()
            if team_id:
                deregister_dynamic_team(team_id)
            return redirect("teams_admin")
        if action == "reset":
            reset_dynamic_registry()
            return redirect("teams_admin")

        # Add / Import flow
        if action == "import":
            import_format = (request.POST.get("import_format") or "json").lower()
            import_data = request.POST.get("import_data") or ""
            overwrite = bool(request.POST.get("overwrite"))
            err = None; added = 0; updated = 0
            try:
                if import_format == "json":
                    import json
                    payload = json.loads(import_data)
                    if isinstance(payload, dict):
                        for tid, entry in payload.items():
                            if not isinstance(entry, dict):
                                continue
                            team_id = "".join(c.lower() if c.isalnum() else "-" for c in (tid or "")).strip("-")
                            if not team_id:
                                continue
                            exists = team_id in load_dynamic_registry()
                            if exists and not overwrite:
                                continue
                            register_dynamic_team(team_id, description=entry.get("description"), llm_profile=entry.get("llm_profile"))
                            if exists:
                                updated += 1
                            else:
                                added += 1
                    else:
                        err = "JSON must be an object of id → entry."
                else:
                    # CSV format
                    lines = [ln for ln in import_data.splitlines() if ln.strip()]
                    if not lines:
                        err = "CSV is empty."
                    else:
                        # Expect header
                        header = [h.strip() for h in lines[0].split(",")]
                        col_id = header.index("id") if "id" in header else 0
                        col_llm = header.index("llm_profile") if "llm_profile" in header else None
                        col_desc = header.index("description") if "description" in header else None
                        for row in lines[1:]:
                            cols = row.split(",")
                            raw_id = cols[col_id] if len(cols) > col_id else ""
                            team_id = "".join(c.lower() if c.isalnum() else "-" for c in raw_id).strip("-")
                            if not team_id:
                                continue
                            llm_profile = (cols[col_llm] if col_llm is not None and len(cols) > col_llm else None)
                            description = (cols[col_desc] if col_desc is not None and len(cols) > col_desc else None)
                            exists = team_id in load_dynamic_registry()
                            if exists and not overwrite:
                                continue
                            register_dynamic_team(team_id, description=description, llm_profile=llm_profile)
                            if exists:
                                updated += 1
                            else:
                                added += 1
            except Exception as e:
                err = f"Import failed: {e}"
            teams = list(load_dynamic_registry().values())
            ctx = {"teams": teams, **_profiles_ctx()}
            if err:
                ctx["error"] = err
            else:
                ctx["message"] = f"Imported: {added} added, {updated} updated."
            return render(request, "teams_admin.html", ctx)

        # Add flow continues
        team_name = (request.POST.get("team_name") or "").strip()
        llm_profile = (request.POST.get("llm_profile") or "").strip() or None
        description = (request.POST.get("description") or "").strip() or None
        teams_current = list(load_dynamic_registry().values())
        # Basic validation
        if not team_name:
            return render(request, "teams_admin.html", {"error": "Team name is required.", "teams": teams_current, **_profiles_ctx()})
        # Slugify: lowercase alnum and '-'
        slug = "".join(c.lower() if c.isalnum() else "-" for c in team_name).strip("-")
        if not slug:
            return render(request, "teams_admin.html", {"error": "Team name must contain letters or numbers.", "teams": teams_current, **_profiles_ctx()})
        if len(slug) > 64:
            return render(request, "teams_admin.html", {"error": "Team name too long (max 64).", "teams": teams_current, **_profiles_ctx()})
        # Uniqueness vs dynamic registry
        if any(t.get("id") == slug for t in teams_current):
            return render(request, "teams_admin.html", {"error": f"Team '{slug}' already exists.", "teams": teams_current, **_profiles_ctx()})
        # Guard against collisions with statically discovered blueprints
        try:
            discovered = discover_blueprints(directories=[BLUEPRINT_DIRECTORY])
            if isinstance(discovered, dict) and slug in discovered:
                return render(request, "teams_admin.html", {"error": f"Name '{slug}' conflicts with an existing blueprint.", "teams": teams_current, **_profiles_ctx()})
        except Exception:
            pass
        register_dynamic_team(slug, description=description, llm_profile=llm_profile)
        return redirect("teams_admin")

    teams = list(load_dynamic_registry().values())
    return render(request, "teams_admin.html", {"teams": teams, **_profiles_ctx()})


def _profiles_ctx():
    """Builds a context dict containing available LLM profile names for form suggestions."""
    profiles: list[str] = []
    try:
        # Prefer repo-local swarm_config.json for demo simplicity
        import json
        cfg_path = Path(settings.BASE_DIR) / "swarm_config.json"
        paths = [cfg_path]
        # Also include XDG user config swarm_config.json
        xdg_cfg = get_user_config_dir_for_swarm() / "swarm_config.json"
        paths.append(xdg_cfg)
        for path in paths:
            if path.exists():
                data = json.loads(path.read_text())
                llm = data.get("llm", {})
                if isinstance(llm, dict):
                    if "profiles" in llm and isinstance(llm["profiles"], dict):
                        profiles.extend(list(llm["profiles"].keys()))
                    else:
                        profiles.extend(list(llm.keys()))
        # De-duplicate while preserving order
        seen = set(); ordered = []
        for p in profiles:
            if p not in seen:
                seen.add(p); ordered.append(p)
        profiles = ordered
    except Exception:
        profiles = []
    return {"profiles": profiles}


@csrf_exempt
def teams_export(request):
    """Export the dynamic team registry as JSON or CSV."""
    reg = load_dynamic_registry()
    fmt = request.GET.get("format", "json").lower()
    if fmt == "csv":
        lines = ["id,llm_profile,description"]
        for k, v in reg.items():
            llm = (v.get("llm_profile") or "").replace(",", " ")
            desc = (v.get("description") or "").replace(",", " ")
            lines.append(f"{k},{llm},{desc}")
        body = "\n".join(lines) + "\n"
        resp = HttpResponse(body, content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=teams.csv"
        return resp
    # default JSON
    return JsonResponse(reg)


def profiles_page(request):
    """Show detected LLM profiles with model/provider/base_url."""
    profiles = []
    try:
        import json
        cfgs = []
        for path in [Path(settings.BASE_DIR) / "swarm_config.json", get_user_config_dir_for_swarm() / "swarm_config.json"]:
            if path.exists():
                cfgs.append(json.loads(path.read_text()))
        seen = set()
        for cfg in cfgs:
            llm = cfg.get("llm", {}) if isinstance(cfg, dict) else {}
            # support both nested profiles and flat mapping
            if "profiles" in llm and isinstance(llm["profiles"], dict):
                iterable = llm["profiles"].items()
            else:
                iterable = llm.items()
            for name, data in iterable:
                if name in seen or not isinstance(data, dict):
                    continue
                seen.add(name)
                profiles.append({
                    "name": name,
                    "provider": data.get("provider"),
                    "model": data.get("model"),
                    "base_url": data.get("base_url"),
                })
    except Exception:
        profiles = []
    return render(request, "profiles.html", {"profiles": profiles})
