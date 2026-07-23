import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as RunserverCommand

from swarm.utils.dotenv_load import load_swarm_dotenv
from swarm.utils.env_utils import (
    get_api_auth_token,
    get_api_auth_tokens,
    is_django_debug,
)

# Project root: …/management/commands → parents[4] == repo root when under src/swarm/
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_swarm_dotenv(project_root=_PROJECT_ROOT)


logger = logging.getLogger(__name__)  # Get logger for command messages


class Command(RunserverCommand):
    help = (
        'Starts a lightweight Web server for development. Swarm API authentication '
        'is ENABLED by default (using API_AUTH_TOKEN); pass --disable-auth to turn '
        'it off for local development (requires DJANGO_DEBUG=true).'
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--enable-auth',
            action='store_true',
            dest='enable_auth',
            help='Deprecated no-op: Swarm API authentication is now enabled by default.',
        )
        parser.add_argument(
            '--disable-auth',
            action='store_true',
            dest='disable_auth',
            help=(
                'Disable Swarm API Key authentication for local development. '
                'Refused unless DJANGO_DEBUG=true.'
            ),
        )

    def handle(self, *args, **options):
        if options.get('enable_auth'):
            logger.info(
                "--enable-auth is deprecated and now a no-op: Swarm API "
                "authentication is enabled by default."
            )

        if options.get('disable_auth'):
            if not is_django_debug():
                raise CommandError(
                    "--disable-auth is only permitted in development "
                    "(DJANGO_DEBUG=true). Refusing to start a production server "
                    "with API authentication disabled."
                )
            settings.ENABLE_API_AUTH = False
            settings.SWARM_API_KEY = None
            settings.SWARM_API_KEYS = []
            logger.warning(
                "Swarm API authentication DISABLED via --disable-auth "
                "(development only). Do NOT use this flag in production."
            )
        else:
            # Default: authentication ON, keyed by API_AUTH_TOKEN(S) / SWARM_API_KEY(S).
            api_keys = get_api_auth_tokens()
            api_key = api_keys[0] if api_keys else get_api_auth_token()
            if api_key:
                settings.ENABLE_API_AUTH = True
                settings.SWARM_API_KEY = api_key
                settings.SWARM_API_KEYS = list(api_keys) if api_keys else [api_key]
                logger.info(
                    "Swarm API authentication ENABLED (default). %d accepted key(s).",
                    len(settings.SWARM_API_KEYS),
                )
            else:
                # No token available. In production settings.py would already have
                # refused to boot (get_enforced_api_auth_token). In debug mode we
                # warn loudly instead of silently allowing anonymous access.
                settings.ENABLE_API_AUTH = False
                settings.SWARM_API_KEY = None
                settings.SWARM_API_KEYS = []
                logger.warning(
                    "API_AUTH_TOKEN not set; Swarm API authentication is INACTIVE "
                    "(allowed only because DJANGO_DEBUG=true). Set API_AUTH_TOKEN "
                    "to require authentication, or pass --disable-auth to silence "
                    "this warning intentionally."
                )

        # Call the original runserver command handler
        super().handle(*args, **options)
