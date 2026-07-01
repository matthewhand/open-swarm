import logging
import logging.config
import os  # Import os

from django.apps import AppConfig

# Import Django settings and logging config
from django.conf import settings

logger = logging.getLogger(__name__)

class SwarmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swarm'
    verbose_name = "Swarm Application"

    def ready(self):
        # Configure logging using the settings dictionary
        # This ensures settings are fully loaded before configuring logging
        try:
            logging.config.dictConfig(settings.LOGGING)
            logger.info("Logging configured successfully via SwarmConfig.ready().")
        except Exception as e:
            # Fallback to basic config if dictConfig fails
            logging.basicConfig(level=logging.INFO)
            logger.critical(
                f"Failed to configure logging using dictConfig: {e}. Using basicConfig.",
                exc_info=True
            )


        # The blueprint discovery and URL registration should ideally happen
        # when blueprints are actually needed or instantiated, often handled
        # by the blueprint loading mechanism itself or specific view logic.
        # Avoid doing heavy discovery or URL manipulation directly in AppConfig.ready
        # unless absolutely necessary and carefully managed, as it can lead to
        # import loops or run before the full Django environment is set up.

        # Example: Trigger necessary setup if needed, but avoid blueprint
        # instantiation here.
        logger.info("Swarm AppConfig ready.")

        # If you need to ensure blueprint modules are loaded early, you could
        # potentially just import the main blueprint discovery module here,
        # but calling discover_blueprints and registering URLs is better done elsewhere.
        # from swarm.extensions.blueprint import blueprint_discovery
        # logger.debug("Ensured blueprint discovery module is loaded.")

        # Removed blueprint discovery and URL registration loop from here.
        # This will now rely on discover_blueprints being called where needed (e.g.,
        # in list_models view)
        # and register_django_components being called by BlueprintBase.__init__.

        # Ensure necessary environment variables for Django are set if not already
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
             os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
             logger.warning(
                "DJANGO_SETTINGS_MODULE not set, setting default 'swarm.settings'"
            )

        # Load the swarm config ONCE and cache it on the AppConfig so every
        # blueprint reads the same file. BlueprintBase._load_configuration already
        # prefers ``apps.get_app_config('swarm').config`` — populating it here from
        # the XDG path is what makes the server honor ~/.config/swarm/swarm_config.json
        # (like swarm-cli does). We load ONLY SWARM_CONFIG_PATH or the XDG path;
        # if neither exists we leave config empty and BlueprintBase's own
        # working-directory fallback still picks up a ./swarm_config.json — so cwd
        # behavior is unchanged, we only *add* XDG.
        self.config = self._load_swarm_config()

        # Resume async /v1/responses tasks left in-flight by a restart — server
        # processes only (not migrate/test), guarded against the runserver
        # reloader's parent process to avoid double-resume.
        self._maybe_resume_async_tasks()

        logger.info("Swarm app initialization checks completed.")

    @staticmethod
    def _maybe_resume_async_tasks() -> None:
        import sys

        if os.environ.get("SWARM_TEST_MODE"):
            return
        argv = " ".join(sys.argv)
        if "runserver" in argv:
            serving = ("--noreload" in argv) or os.environ.get("RUN_MAIN") == "true"
        else:
            serving = any(s in argv for s in ("swarm-api", "daphne", "uvicorn", "gunicorn"))
        if not serving:
            return
        try:
            import threading

            from swarm.views.responses_views import resume_pending_responses

            threading.Thread(target=resume_pending_responses, daemon=True).start()
        except Exception as e:  # never let resume break startup
            logger.warning("Could not schedule async-task resume: %s", e)

    @staticmethod
    def _load_swarm_config() -> dict:
        """Resolve + load swarm_config.json (XDG-aware), env-substituted. Never raises.

        Loads the JSON leniently (no ``llm``-section requirement) — a CLI-fusion
        gateway config is often ``cli_agents``-only, and the validation in
        ``config_loader.load_config`` would otherwise reject it and lose the config.
        """
        import json
        from pathlib import Path

        from swarm.core import config_loader

        try:
            env_path = os.environ.get("SWARM_CONFIG_PATH")
            if env_path and Path(env_path).is_file():
                path = Path(env_path)
            else:
                # XDG only here; ./swarm_config.json is handled by BlueprintBase's
                # own cwd fallback so we don't change cwd behavior (or break tests
                # that simulate "no config files").
                xdg = config_loader._xdg_config_path()
                path = xdg if xdg.is_file() else None
            if not path:
                # XDG only here; ./swarm_config.json is handled by BlueprintBase's
                # own cwd fallback (which does the env bootstrap synthesis for simple case).
                # This method must return {} for missing config (as documented and tested).
                logger.info("No XDG/SWARM_CONFIG_PATH swarm_config.json; deferring to cwd fallback.")
                return {}
            raw = json.loads(Path(path).read_text())
            cfg = config_loader._substitute_env_vars(raw)
            logger.info("Swarm config loaded from %s", path)
            return cfg if isinstance(cfg, dict) else {}
        except Exception as e:
            logger.warning("Failed to load swarm config (%s); using empty config.", e)
            return {}

