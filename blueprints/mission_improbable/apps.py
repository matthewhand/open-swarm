from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class MissionImprobableConfig(AppConfig):
    name = 'blueprints.mission_improbable'
    verbose_name = "Mission Improbable Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
