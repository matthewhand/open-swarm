import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class GAWDConfig(AppConfig):
    name = 'blueprints.gawd'  # Normalized name
    verbose_name = "GAWD Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
