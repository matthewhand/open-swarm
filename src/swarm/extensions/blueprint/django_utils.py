"""
Django integration utilities for blueprint extensions.
"""

import logging
import os
import importlib.util
import sys  # Import sys
import inspect # Import inspect
from typing import Any, TYPE_CHECKING
from django.conf import settings # Import settings directly
# Import necessary URL handling functions
from django.urls import clear_url_caches, get_resolver, get_urlconf, set_urlconf, URLPattern, URLResolver, path, include # Added path, include
from django.utils.module_loading import import_module # More standard way to import
from collections import OrderedDict
from django.apps import apps as django_apps

# Use TYPE_CHECKING to avoid circular import issues if BlueprintBase imports this indirectly
if TYPE_CHECKING:
    from .blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

def register_django_components(blueprint: 'BlueprintBase') -> None:
    """Register Django settings and URLs if applicable for the given blueprint."""
    # Use getattr to safely check _urls_registered, default to False if not present
    if blueprint.skip_django_registration or getattr(blueprint, "_urls_registered", False):
        logger.debug(f"Skipping Django registration for {blueprint.__class__.__name__}: Skipped by flag or already registered.")
        return
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        logger.debug("Skipping Django registration: DJANGO_SETTINGS_MODULE not set.")
        return

    try:
        # App readiness check less critical now if called within test fixtures after setup
        # but still useful to avoid redundant work during normal server startup.
        # Let's assume if DJANGO_SETTINGS_MODULE is set, setup has likely happened or will happen.
        # if not django_apps.ready and not getattr(settings, 'TESTING', False):
        #     logger.debug("Django apps not ready; registration likely handled by AppConfig.ready().")
        #     return

        _load_local_settings(blueprint)
        _merge_installed_apps(blueprint) # Attempt merge

        if hasattr(blueprint, 'register_blueprint_urls') and callable(blueprint.register_blueprint_urls):
             logger.debug(f"Calling blueprint-specific register_blueprint_urls for {blueprint.__class__.__name__}")
             blueprint.register_blueprint_urls()
             # Assume the custom function sets _urls_registered if it succeeds
             # blueprint._urls_registered = True # Let the custom function handle this flag
        else:
             logger.debug(f"Using generic URL registration for {blueprint.__class__.__name__}")
             _register_blueprint_urls_generic(blueprint)

    except ImportError as e:
        # Catch cases where Django itself or essential parts are not installed/available
        logger.warning(f"Django not fully available; skipping Django component registration for {blueprint.__class__.__name__}. Error: {e}")
    except Exception as e:
        logger.error(f"Failed to register Django components for {blueprint.__class__.__name__}: {e}", exc_info=True)


def _load_local_settings(blueprint: 'BlueprintBase') -> None:
    """Load local settings.py from the blueprint's directory if it exists.
       Handles being called when the blueprint module is '__main__'.
    """
    local_settings_path = None
    settings_module_name = None # A unique name for the loaded settings module

    try:
        module_name = blueprint.__class__.__module__

        if module_name == "__main__":
            # --- Handling direct script execution ---
            logger.debug(f"Blueprint class module is '__main__'. Determining path from file location.")
            try:
                # Get the path to the file where the blueprint class is defined
                blueprint_file_path = inspect.getfile(blueprint.__class__)
                blueprint_dir = os.path.dirname(blueprint_file_path)
                local_settings_path = os.path.join(blueprint_dir, "settings.py")
                # Create a unique, safe module name based on the blueprint class
                # Using a prefix to avoid potential clashes with real modules
                settings_module_name = f"_swarm_local_settings_{blueprint.__class__.__name__}"
                logger.debug(f"Derived potential local settings path for __main__: {local_settings_path}")
            except TypeError as e:
                logger.error(f"Could not determine file path for blueprint class {blueprint.__class__.__name__} when run as __main__: {e}")
                setattr(blueprint, 'local_settings', None) # Ensure attribute exists
                return
            except Exception as e:
                logger.error(f"Unexpected error getting blueprint file path for __main__: {e}", exc_info=True)
                setattr(blueprint, 'local_settings', None)
                return
        else:
            # --- Handling standard import execution ---
            logger.debug(f"Blueprint class module is '{module_name}'. Using importlib.")
            try:
                module_spec = importlib.util.find_spec(module_name)
                if module_spec and module_spec.origin:
                    blueprint_dir = os.path.dirname(module_spec.origin)
                    local_settings_path = os.path.join(blueprint_dir, "settings.py")
                    # Use a name relative to the original module to avoid clashes
                    settings_module_name = f"{module_name}.local_settings"
                    logger.debug(f"Derived potential local settings path via importlib: {local_settings_path}")
                else:
                    logger.debug(f"Could not find module spec or origin for '{module_name}'. Cannot determine local settings path.")
                    setattr(blueprint, 'local_settings', None)
                    return
            except Exception as e: # Catch potential errors during find_spec
                 logger.error(f"Error finding spec for module '{module_name}': {e}", exc_info=True)
                 setattr(blueprint, 'local_settings', None)
                 return

        # --- Common Loading Logic ---
        if local_settings_path and os.path.isfile(local_settings_path):
            # Check if already loaded (using the determined name)
            if settings_module_name in sys.modules:
                logger.debug(f"Local settings module '{settings_module_name}' already loaded. Assigning.")
                blueprint.local_settings = sys.modules[settings_module_name]
                # Optionally, re-apply settings if your local_settings has an apply function
                # if hasattr(blueprint.local_settings, 'apply_settings'):
                #    blueprint.local_settings.apply_settings()
                return

            spec = importlib.util.spec_from_file_location(settings_module_name, local_settings_path)
            if spec and spec.loader:
                local_settings = importlib.util.module_from_spec(spec)
                # Add to sys.modules BEFORE execution to handle potential internal imports
                sys.modules[settings_module_name] = local_settings
                blueprint.local_settings = local_settings # Assign early
                logger.info(f"Loading and executing local settings from '{local_settings_path}' as '{settings_module_name}' for '{blueprint.__class__.__name__}'.")
                spec.loader.exec_module(local_settings)
                logger.debug(f"Finished executing local settings module '{settings_module_name}'.")
            else:
                logger.warning(f"Could not create module spec/loader for local settings at '{local_settings_path}'")
                setattr(blueprint, 'local_settings', None)
        else:
            logger.debug(f"No local settings file found at '{local_settings_path}' for {blueprint.__class__.__name__}.")
            setattr(blueprint, 'local_settings', None)

    except Exception as e:
        logger.error(f"Error loading local settings for {blueprint.__class__.__name__}: {e}", exc_info=True)
        # Explicitly check for the original error if needed
        if isinstance(e, ValueError) and "__spec__ is None" in str(e):
            logger.critical("Original Error Context: Failed during importlib processing, likely due to __main__ module details.")
        setattr(blueprint, 'local_settings', None) # Ensure attribute exists even on error


def _merge_installed_apps(blueprint: 'BlueprintBase') -> None:
    """Merge INSTALLED_APPS from blueprint's local settings into main Django settings.
       Note: This might require a server restart/reload to take full effect.
    """
    # Check if local_settings was successfully loaded and has INSTALLED_APPS
    if hasattr(blueprint, "local_settings") and blueprint.local_settings and hasattr(blueprint.local_settings, "INSTALLED_APPS"):
        try:
            blueprint_apps = getattr(blueprint.local_settings, "INSTALLED_APPS", [])
            if not isinstance(blueprint_apps, (list, tuple)):
                 logger.warning(f"Blueprint {blueprint.__class__.__name__}'s local INSTALLED_APPS is not a list or tuple.")
                 return

            # Ensure settings.INSTALLED_APPS is available and is a list
            if not hasattr(settings, 'INSTALLED_APPS'):
                logger.error("Cannot merge apps: django.conf.settings.INSTALLED_APPS is not defined.")
                return
            if isinstance(settings.INSTALLED_APPS, tuple):
                 settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)
            elif not isinstance(settings.INSTALLED_APPS, list):
                 logger.error(f"Cannot merge apps: django.conf.settings.INSTALLED_APPS is not a list or tuple (type: {type(settings.INSTALLED_APPS)}).")
                 return

            apps_added_names = []
            for app in blueprint_apps:
                if app not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(app) # Directly modify the list
                    apps_added_names.append(app)
                    logger.debug(f"Added app '{app}' from blueprint {blueprint.__class__.__name__} to INSTALLED_APPS in settings.")

            if apps_added_names:
                 logger.info(f"Merged INSTALLED_APPS from blueprint {blueprint.__class__.__name__}: {apps_added_names}. App registry reload/server restart might be needed.")

                 # Attempt app registry reload - Use with extreme caution! Can lead to instability.
                 # It's generally safer to rely on server restart/reload mechanisms.
                 if getattr(settings, 'AUTO_RELOAD_APP_REGISTRY', False): # Add a setting to control this
                     try:
                         logger.warning("Attempting to dynamically reload Django app registry (Experimental)...")
                         django_apps.app_configs = OrderedDict()
                         django_apps.ready = False
                         django_apps.clear_cache()
                         django_apps.populate(settings.INSTALLED_APPS)
                         logger.info("Successfully reloaded Django app registry.")
                     except RuntimeError as e:
                          logger.error(f"Could not reload app registry (likely reentrant call): {e}")
                     except Exception as e:
                          logger.error(f"Error reloading Django app registry: {e}", exc_info=True)
                 else:
                      logger.debug("Automatic app registry reload is disabled (settings.AUTO_RELOAD_APP_REGISTRY=False).")

        except ImportError:
             # This might happen if django.conf.settings itself wasn't importable earlier
             logger.error("Could not import or access django.conf.settings to merge INSTALLED_APPS.")
        except Exception as e:
            logger.error(f"Error merging INSTALLED_APPS for {blueprint.__class__.__name__}: {e}", exc_info=True)
    else:
        logger.debug(f"No local settings or INSTALLED_APPS found for blueprint {blueprint.__class__.__name__} to merge.")


def _register_blueprint_urls_generic(blueprint: 'BlueprintBase') -> None:
    """Generic function to register blueprint URLs based on metadata.
       Dynamically adds patterns to the root urlconf's urlpatterns list.
    """
    # Check if already done for this blueprint instance
    if getattr(blueprint, "_urls_registered", False):
        logger.debug(f"URLs for {blueprint.__class__.__name__} already marked as registered.")
        return

    # Safely get metadata attributes
    metadata = getattr(blueprint, 'metadata', {})
    if not isinstance(metadata, dict):
         logger.warning(f"Blueprint {blueprint.__class__.__name__} metadata is not a dictionary. Skipping URL registration.")
         return
    django_modules = metadata.get("django_modules", {})
    module_path = django_modules.get("urls")
    url_prefix = metadata.get("url_prefix", "")

    if not module_path:
        logger.debug(f"No 'urls' module specified in metadata for {blueprint.__class__.__name__}; skipping generic URL registration.")
        return

    try:
        root_urlconf_name = settings.ROOT_URLCONF
        if not root_urlconf_name:
             logger.error("settings.ROOT_URLCONF is not set. Cannot register URLs.")
             return

        # --- Get the root urlpatterns list dynamically ---
        try:
             # Use Django's utility function for importing
             root_urlconf_module = import_module(root_urlconf_name)
             if not hasattr(root_urlconf_module, 'urlpatterns') or not isinstance(root_urlconf_module.urlpatterns, list):
                  logger.error(f"Cannot modify urlpatterns in '{root_urlconf_name}'. 'urlpatterns' attribute is missing or not a list.")
                  return
             root_urlpatterns = root_urlconf_module.urlpatterns
        except ImportError:
             logger.error(f"Could not import main URLconf '{root_urlconf_name}' to modify urlpatterns.")
             return
        except Exception as e:
             logger.error(f"Error accessing urlpatterns in '{root_urlconf_name}': {e}", exc_info=True)
             return

        # Import the blueprint's URL module
        try:
            urls_module = import_module(module_path)
            if not hasattr(urls_module, "urlpatterns"):
                logger.debug(f"Blueprint URL module '{module_path}' has no 'urlpatterns'. Skipping.")
                # Mark as registered even if no patterns, to avoid re-attempting
                blueprint._urls_registered = True
                return
        except ImportError:
            logger.error(f"Could not import blueprint URL module: '{module_path}'")
            return
        except Exception as e:
             logger.error(f"Error importing or accessing urlpatterns in '{module_path}': {e}", exc_info=True)
             return

        # Prepare the new pattern
        if url_prefix and not url_prefix.endswith('/'): url_prefix += '/'
        # Use blueprint's cli_name or class name as app_name for namespacing
        app_name = metadata.get("cli_name", blueprint.__class__.__name__.lower().replace('blueprint', ''))
        # Include the module directly for `include` to find its `urlpatterns`
        new_pattern = path(url_prefix, include((urls_module, app_name))) # Pass tuple (module, app_name)

        # Check if an identical pattern (prefix + app_name) already exists
        already_exists = False
        for existing_pattern in root_urlpatterns:
             # Check if it's a resolver (include()) and compare prefix and app_name
             if (isinstance(existing_pattern, URLResolver) and
                 str(existing_pattern.pattern) == str(new_pattern.pattern) and # Compare URL prefix pattern
                 getattr(existing_pattern, 'app_name', None) == app_name):     # Compare app_name
                  logger.warning(f"URL pattern for prefix '{url_prefix}' and app '{app_name}' seems already registered in '{root_urlconf_name}'. Skipping.")
                  already_exists = True
                  break

        if not already_exists:
            root_urlpatterns.append(new_pattern)
            logger.info(f"Dynamically registered URLs from '{module_path}' at prefix '{url_prefix}' (app_name: '{app_name}') into '{root_urlconf_name}'.")

            # --- Force update of URL resolver (Important!) ---
            clear_url_caches()
            # Reloading the root URLconf module is generally needed for changes to take effect
            try:
                importlib.reload(root_urlconf_module)
                logger.debug(f"Reloaded root URLconf module: {root_urlconf_name}")
            except Exception as e:
                 logger.error(f"Failed to reload root URLconf module '{root_urlconf_name}': {e}")
                 logger.warning("URL changes might not be active until server restart.")

            # Explicitly reset the URLconf to force Django to re-read it
            set_urlconf(None)
            logger.debug(f"Cleared URL caches and reset urlconf. Django should rebuild resolver on next request.")

        # Mark this blueprint instance as having its URLs registered (or attempted)
        blueprint._urls_registered = True

    except ImportError as e:
        logger.error(f"Import error during URL registration for {blueprint.__class__.__name__}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error registering URLs for {blueprint.__class__.__name__}: {e}", exc_info=True)

