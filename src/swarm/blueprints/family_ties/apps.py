import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class FamilyTiesConfig(AppConfig):
    name = 'blueprints.family_ties'
    verbose_name = "Family Ties Blueprint"

    def ready(self):
        logger.debug(f"Registering {self.name} via AppConfig")
