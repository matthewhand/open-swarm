import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as RunserverCommand
from dotenv import load_dotenv

from swarm.utils.env_utils import get_api_auth_token, get_api_auth_tokens, is_django_debug

# Load .env from project root relative to this file's location
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
# Check if .env exists before trying to load
dotenv_path = BASE_DIR / '.env'
if dotenv_path.is_file():
    load_dotenv(dotenv_path=dotenv_path)
else:
    # Optionally log if .env is missing, but don't require it
    # logger = logging.getLogger(__name__) # Get logger if needed here
    # logger.debug(".env file not found in project root, relying solely on environment variables.")
    pass


logger = logging.getLogger(__name__) # Get logger for command messages

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
