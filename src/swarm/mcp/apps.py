from django.apps import AppConfig


class MCPIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm.mcp'

    def ready(self):  # pragma: no cover - exercised in integration tests explicitly
        try:
            from django.conf import settings as dj_settings
            if getattr(dj_settings, 'ENABLE_MCP_SERVER', False):
                from .integration import register_blueprints_with_mcp
                register_blueprints_with_mcp()
        except Exception:
            # Keep startup robust even if MCP integration is misconfigured
            pass

