from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class StewieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm.blueprints.stewie'
    verbose_name = "Family Ties Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
