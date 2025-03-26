from django.apps import AppConfig
import logging
import os # Import os
# Import Django settings and logging config
from django.conf import settings
import logging.config

logger = logging.getLogger(__name__)

class SwarmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm'
    verbose_name = "Swarm Application"

    def ready(self):
        # Configure logging using the settings dictionary
        # This ensures settings are fully loaded before configuring logging
        try:
            logging.config.dictConfig(settings.LOGGING)
            logger.info("Logging configured successfully via SwarmConfig.ready().")
        except Exception as e:
            # Fallback to basic config if dictConfig fails
            logging.basicConfig(level=logging.INFO)
            logger.critical(f"Failed to configure logging using dictConfig: {e}. Using basicConfig.", exc_info=True)


        # The blueprint discovery and URL registration should ideally happen
        # when blueprints are actually needed or instantiated, often handled
        # by the blueprint loading mechanism itself or specific view logic.
        # Avoid doing heavy discovery or URL manipulation directly in AppConfig.ready
        # unless absolutely necessary and carefully managed, as it can lead to
        # import loops or run before the full Django environment is set up.

        # Example: Trigger necessary setup if needed, but avoid blueprint instantiation here.
        logger.info("Swarm AppConfig ready.")

        # If you need to ensure blueprint modules are loaded early, you could
        # potentially just import the main blueprint discovery module here,
        # but calling discover_blueprints and registering URLs is better done elsewhere.
        # from swarm.extensions.blueprint import blueprint_discovery
        # logger.debug("Ensured blueprint discovery module is loaded.")

        # Removed blueprint discovery and URL registration loop from here.
        # This will now rely on discover_blueprints being called where needed (e.g., in list_models view)
        # and register_django_components being called by BlueprintBase.__init__.

        # Ensure necessary environment variables for Django are set if not already
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
             os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
             logger.warning("DJANGO_SETTINGS_MODULE not set, setting default 'swarm.settings'")

        logger.info("Swarm app initialization checks completed.")

