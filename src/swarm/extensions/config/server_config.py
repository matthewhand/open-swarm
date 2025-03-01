"""
Module for managing server configuration files, including saving and validation.

Provides utilities to save configurations to disk and ensure integrity of data.
"""

import json
import os
import logging
from swarm.utils.redact import redact_sensitive_data

# Initialize logger for this module
logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")  # Define DEBUG locally
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
stream_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(stream_handler)

def save_server_config(config: dict, file_path: str = None) -> None:
    """
    Saves the server configuration to a JSON file.

    Args:
        config (dict): The configuration dictionary to save.
        file_path (str): The path to save the configuration file. Defaults to 'swarm_settings.json' in the current directory.

    Raises:
        ValueError: If the configuration is not a valid dictionary.
        OSError: If there are issues writing to the file.
    """
    if not isinstance(config, dict):
        logger.error("Provided configuration is not a dictionary.")
        raise ValueError("Configuration must be a dictionary.")

    if file_path is None:
        file_path = os.path.join(os.getcwd(), "swarm_settings.json")

    logger.debug(f"Saving server configuration to {file_path}")
    try:
        with open(file_path, "w") as file:
            json.dump(config, file, indent=4)
            logger.info(f"Configuration successfully saved to {file_path}")
            logger.debug(f"Saved configuration: {redact_sensitive_data(config)}")
    except OSError as e:
        logger.error(f"Error saving configuration to {file_path}: {e}")
        raise
