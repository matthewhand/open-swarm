import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

def update_installed_apps(settings):
    blueprint_app = "blueprints.chc"
    if blueprint_app not in settings.get("INSTALLED_APPS", []):
        settings["INSTALLED_APPS"].append(blueprint_app)

try:
    update_installed_apps(globals())
except Exception as e:
    logger.error("CHC update failed: %s", e)

CORS_ALLOW_ALL_ORIGINS = True
