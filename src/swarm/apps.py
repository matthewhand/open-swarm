from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class SwarmConfig(AppConfig):
    name = 'swarm'
    verbose_name = "Swarm Application"

    def ready(self):
        # Import views as per original requirement
        from . import views
        logger.debug("Swarm app ready, views imported.")
