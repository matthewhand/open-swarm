"""
Django integration utilities for blueprint extensions.
"""

import logging
import os
import importlib.util
from typing import Any, TYPE_CHECKING
from django.conf import settings # Import settings directly
# Import necessary URL handling functions
from django.urls import clear_url_caches, get_resolver, get_urlconf, set_urlconf, URLPattern, URLResolver
from collections import OrderedDict
from django.apps import apps as django_apps

# Use TYPE_CHECKING to avoid circular import issues if BlueprintBase imports this indirectly
if TYPE_CHECKING:
    from .blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

def register_django_components(blueprint: 'BlueprintBase') -> None:
    """Register Django settings and URLs if applicable for the given blueprint."""
    if blueprint.skip_django_registration or getattr(blueprint, "_urls_registered", False):
        logger.debug(f"Skipping Django registration for {blueprint.__class__.__name__}: Skipped by flag or already registered.")
        return
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        logger.debug("Skipping Django registration: DJANGO_SETTINGS_MODULE not set.")
        return

    try:
        # App readiness check less critical now if called within test fixtures after setup
        if not django_apps.ready and not getattr(settings, 'TESTING', False):
            logger.debug("Django apps not ready; registration likely handled by AppConfig.ready().")
            return

        _load_local_settings(blueprint)
        _merge_installed_apps(blueprint) # Still attempt, might need restart/reload

        if hasattr(blueprint, 'register_blueprint_urls') and callable(blueprint.register_blueprint_urls):
             logger.debug(f"Calling blueprint-specific register_blueprint_urls for {blueprint.__class__.__name__}")
             blueprint.register_blueprint_urls()
             blueprint._urls_registered = True
        else:
             logger.debug(f"Using generic URL registration for {blueprint.__class__.__name__}")
             _register_blueprint_urls_generic(blueprint)

    except ImportError:
        logger.warning("Django not available; skipping Django component registration.")
    except Exception as e:
        logger.error(f"Failed to register Django components for {blueprint.__class__.__name__}: {e}", exc_info=True)

def _load_local_settings(blueprint: 'BlueprintBase') -> None:
    """Load local settings.py from the blueprint's directory if it exists."""
    try:
        module_spec = importlib.util.find_spec(blueprint.__class__.__module__)
        if module_spec and module_spec.origin:
            blueprint_dir = os.path.dirname(module_spec.origin)
            local_settings_path = os.path.join(blueprint_dir, "settings.py")
            if os.path.isfile(local_settings_path):
                spec = importlib.util.spec_from_file_location(f"{blueprint.__class__.__module__}.local_settings", local_settings_path)
                if spec and spec.loader:
                    local_settings = importlib.util.module_from_spec(spec)
                    blueprint.local_settings = local_settings
                    spec.loader.exec_module(local_settings)
                    logger.debug(f"Loaded local settings from {local_settings_path} for {blueprint.__class__.__name__}")
                else:
                    logger.warning(f"Could not create module spec for local settings at {local_settings_path}")
                    blueprint.local_settings = None
            else: blueprint.local_settings = None
        else: blueprint.local_settings = None
    except Exception as e:
        logger.error(f"Error loading local settings for {blueprint.__class__.__name__}: {e}", exc_info=True)
        blueprint.local_settings = None


def _merge_installed_apps(blueprint: 'BlueprintBase') -> None:
    """Merge INSTALLED_APPS from blueprint's local settings into main Django settings."""
    if hasattr(blueprint, "local_settings") and blueprint.local_settings and hasattr(blueprint.local_settings, "INSTALLED_APPS"):
        try:
            blueprint_apps = getattr(blueprint.local_settings, "INSTALLED_APPS", [])
            if not isinstance(blueprint_apps, (list, tuple)):
                 logger.warning(f"Blueprint {blueprint.__class__.__name__}'s local INSTALLED_APPS is not a list or tuple.")
                 return

            apps_added = False
            if isinstance(settings.INSTALLED_APPS, tuple):
                settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)

            for app in blueprint_apps:
                if app not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(app)
                    apps_added = True
                    logger.debug(f"Added app '{app}' from blueprint {blueprint.__class__.__name__} to INSTALLED_APPS.")

            if apps_added:
                 logger.info(f"Merged INSTALLED_APPS from blueprint {blueprint.__class__.__name__}. App registry reload might be needed.")
                 # Attempt app registry reload - Use with caution!
                 try:
                     logger.debug("Attempting to reload Django app registry...")
                     django_apps.app_configs = OrderedDict()
                     django_apps.ready = False
                     django_apps.clear_cache()
                     django_apps.populate(settings.INSTALLED_APPS)
                     logger.info("Successfully reloaded Django app registry.")
                 except RuntimeError as e:
                      logger.error(f"Could not reload app registry (likely reentrant call): {e}")
                 except Exception as e:
                      logger.error(f"Error reloading Django app registry: {e}", exc_info=True)


        except ImportError:
             logger.error("Could not import django.conf.settings to merge INSTALLED_APPS.")
        except Exception as e:
            logger.error(f"Error merging INSTALLED_APPS for {blueprint.__class__.__name__}: {e}", exc_info=True)

def _register_blueprint_urls_generic(blueprint: 'BlueprintBase') -> None:
    """Generic function to register blueprint URLs based on metadata."""
    if getattr(blueprint, "_urls_registered", False):
        logger.debug(f"URLs for {blueprint.__class__.__name__} already registered.")
        return

    module_path = blueprint.metadata.get("django_modules", {}).get("urls")
    url_prefix = blueprint.metadata.get("url_prefix", "")

    if not module_path:
        logger.debug(f"No 'urls' module specified in metadata for {blueprint.__class__.__name__}; skipping generic URL registration.")
        return

    try:
        from django.urls import include, path
        from importlib import import_module

        root_urlconf_name = settings.ROOT_URLCONF
        if not root_urlconf_name:
             logger.error("settings.ROOT_URLCONF is not set.")
             return

        # --- Get the root urlpatterns list directly ---
        # This is potentially fragile if ROOT_URLCONF itself changes, but necessary for tests
        try:
             root_urlconf_module = import_module(root_urlconf_name)
             if not hasattr(root_urlconf_module, 'urlpatterns') or not isinstance(root_urlconf_module.urlpatterns, list):
                  logger.error(f"Cannot modify urlpatterns in '{root_urlconf_name}'. It's missing or not a list.")
                  return
             root_urlpatterns = root_urlconf_module.urlpatterns
        except ImportError:
             logger.error(f"Could not import main URLconf '{root_urlconf_name}' to modify urlpatterns.")
             return

        # Import the blueprint's URL module
        try:
            urls_module = import_module(module_path)
            if not hasattr(urls_module, "urlpatterns"):
                logger.debug(f"Blueprint URL module '{module_path}' has no 'urlpatterns'.")
                blueprint._urls_registered = True
                return
        except ImportError:
            logger.error(f"Could not import blueprint URL module: '{module_path}'")
            return

        if url_prefix and not url_prefix.endswith('/'): url_prefix += '/'
        app_name = blueprint.metadata.get("cli_name", blueprint.__class__.__name__.lower())
        new_pattern = path(url_prefix, include((urls_module, app_name)))

        # Check if an identical pattern already exists
        already_exists = False
        for existing_pattern in root_urlpatterns:
             # Compare based on pattern regex and included module/app_name if possible
             if (isinstance(existing_pattern, (URLPattern, URLResolver)) and
                 str(existing_pattern.pattern) == str(new_pattern.pattern) and
                 getattr(existing_pattern, 'app_name', None) == app_name and
                 getattr(existing_pattern, 'namespace', None) == getattr(new_pattern, 'namespace', None)): # Check namespace too
                  # A bit more robust check, might need refinement
                  logger.warning(f"URL pattern for prefix '{url_prefix}' and app '{app_name}' seems already registered. Skipping.")
                  already_exists = True
                  break

        if not already_exists:
            root_urlpatterns.append(new_pattern)
            logger.info(f"Dynamically registered URLs from '{module_path}' at prefix '{url_prefix}' (app_name: '{app_name}')")

            # --- Force update of URL resolver ---
            clear_url_caches()
            # Reload the root URLconf module itself
            try:
                reload(root_urlconf_module)
                logger.debug(f"Reloaded root URLconf module: {root_urlconf_name}")
            except Exception as e:
                 logger.error(f"Failed to reload root URLconf module: {e}")
            # Try setting urlconf to None to force re-reading from settings
            set_urlconf(None)
            # Explicitly getting the resolver again might help
            resolver = get_resolver(get_urlconf())
            resolver._populate() # Re-populate cache
            logger.info(f"Cleared URL caches and attempted to refresh resolver for {root_urlconf_name}.")

        blueprint._urls_registered = True

    except ImportError as e:
        logger.error(f"Import error during URL registration for {blueprint.__class__.__name__}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error registering URLs for {blueprint.__class__.__name__}: {e}", exc_info=True)

