from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class WhiskeyTangoFoxtrotConfig(AppConfig):
    name = 'blueprints.whiskeytango_foxtrot'  # Normalized name
    verbose_name = "Whiskey Tango Foxtrot Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
