from django.apps import AppConfig
from swarm.extensions.blueprint import discover_blueprints

class SwarmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm'

    def ready(self):
        from . import views
        views.blueprints_metadata = discover_blueprints(directories=["blueprints"])
