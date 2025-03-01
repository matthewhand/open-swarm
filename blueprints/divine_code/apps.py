from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class DivineCodeConfig(AppConfig):
    name = 'blueprints.divine_code'  # Normalized name
    verbose_name = "Divine Code Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
