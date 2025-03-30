import os
import logging
from django.core.management.commands.runserver import Command as RunserverCommand
from django.conf import settings
from dotenv import load_dotenv
from pathlib import Path

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
    help = 'Starts a lightweight Web server for development, with an option to enable Swarm API authentication.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--enable-auth',
            action='store_true',
            dest='enable_auth',
            help='Enable Swarm API Key authentication using API_AUTH_TOKEN from environment/.env.', # Updated help text
        )

    def handle(self, *args, **options):
        enable_auth_flag = options.get('enable_auth', False)
        api_key = None # Keep internal variable name simple

        if enable_auth_flag:
            settings.ENABLE_API_AUTH = True # Override setting
            # *** Use API_AUTH_TOKEN from environment ***
            api_key = os.getenv('API_AUTH_TOKEN')
            if api_key:
                settings.SWARM_API_KEY = api_key # Store the key in settings
                logger.info("Swarm API authentication ENABLED via --enable-auth flag. API_AUTH_TOKEN found.")
            else:
                settings.SWARM_API_KEY = None # Ensure it's None if not found
                logger.warning("Swarm API authentication ENABLED via --enable-auth flag, but API_AUTH_TOKEN not found in environment/.env. API will allow anonymous access if session auth fails.")
        else:
            # Keep defaults from settings.py (ENABLE_API_AUTH=False, SWARM_API_KEY=None)
            # Ensure SWARM_API_KEY is explicitly None if auth is disabled
            settings.ENABLE_API_AUTH = False
            settings.SWARM_API_KEY = None
            logger.info("Swarm API authentication DISABLED (run with --enable-auth and set API_AUTH_TOKEN to activate).")

        # Call the original runserver command handler
        super().handle(*args, **options)

