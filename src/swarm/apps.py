from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class SwarmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm'
    verbose_name = "Swarm Application"

    def ready(self):
        from . import views
        from swarm.extensions.blueprint import discover_blueprints

        try:
            blueprints_metadata = discover_blueprints(directories=["blueprints"])
            views.blueprints_metadata = blueprints_metadata
            loaded_blueprints = list(blueprints_metadata.keys())
            logger.debug(f"Loaded Blueprints: {', '.join(loaded_blueprints) if loaded_blueprints else 'None'}")
            
            # Register URLs immediately
            for blueprint_name in loaded_blueprints:
                blueprint_class = blueprints_metadata[blueprint_name].get("blueprint_class")
                if blueprint_class:
                    blueprint_instance = blueprint_class(config={})
                    blueprint_instance.register_blueprint_urls()
                    logger.info(f"Registered URLs for blueprint: {blueprint_name}")
        except Exception as e:
            logger.error(f"Failed during blueprint loading or URL registration: {e}", exc_info=True)
        
        logger.info("Swarm app initialization completed.")
