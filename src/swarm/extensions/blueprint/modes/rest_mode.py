import logging
import os
import subprocess
import sys

from swarm.utils.color_utils import color_text

logger = logging.getLogger(__name__)

def run_rest_mode(agent):
    """
    Launches the Django development server to serve REST endpoints.

    Args:
        agent: The agent object passed in by main.py, not actually used here.
    """
    try:
        logger.info("Launching Django server for REST mode...")

        # Retrieve host and port from environment variables, defaulting to 0.0.0.0:8000
        host = os.getenv("HOST", "0.0.0.0")
        port = os.getenv("PORT", "8000")

        logger.info(f"Using host '{host}' and port '{port}' for the Django server.")
        print(color_text(f"Starting Django REST server on http://{host}:{port}", "cyan"))

        # Use subprocess to run the Django server with the specified host and port
        subprocess.run(
            [sys.executable, "manage.py", "runserver", f"{host}:{port}"],
            check=True
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to launch Django server: {e}")
        print(color_text(f"Failed to launch Django server: {e}", "red"))
    except Exception as e:
        logger.error(f"Unexpected error in run_rest_mode: {e}", exc_info=True)
        print(color_text(f"Unexpected error in run_rest_mode: {e}", "red"))
