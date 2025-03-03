"""
General-purpose utility functions for the Swarm framework.
"""

import os
import logging
import jmespath
import json
import datetime
from typing import Optional
from swarm.utils.logger_setup import setup_logger

# Initialize logger for this module
logger = setup_logger(__name__)

def find_project_root(current_path: str, marker: str = ".git") -> str:
    """
    Recursively search for the project root by looking for a specific marker file or directory.

    Args:
        current_path (str): Starting path for the search.
        marker (str): Marker file or directory to identify the project root.

    Returns:
        str: Path to the project root.

    Raises:
        FileNotFoundError: If the project root cannot be found.
    """
    while True:
        if os.path.exists(os.path.join(current_path, marker)):
            return current_path
        new_path = os.path.dirname(current_path)
        if new_path == current_path:
            break
        current_path = new_path
    raise FileNotFoundError(f"Project root with marker '{marker}' not found.")

def color_text(text: str, color: str = "white") -> str:
    """
    Returns colored text using ANSI escape codes.

    Args:
        text (str): Text to color.
        color (str): Color name. Supported colors: red, green, yellow, blue, magenta, cyan, white.

    Returns:
        str: Colored text string.
    """
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
    }
    reset = "\033[0m"
    color_code = colors.get(color.lower(), colors["white"])
    return f"{color_code}{text}{reset}"

def extract_chat_id(payload: dict) -> str:
    """
    Extracts `conversation_id` from the last assistant's tool call.

    Extracts the JSON string from `function.arguments`, parses it inline,
    and returns only `conversation_id`.
    """
    try:
        path_expr = os.getenv("STATEFUL_CHAT_ID_PATH", "").strip()
        logger.debug(f"Extracting chat ID using JMESPath: {path_expr}")
        if not path_expr:
            logger.warning("STATEFUL_CHAT_ID_PATH is empty.")
            return ""
        extracted = jmespath.search(path_expr, payload)
        if extracted:
            if isinstance(extracted, str):
                stripped = extracted.strip()
                if stripped.startswith('{') or stripped.startswith('['):
                    try:
                        parsed = json.loads(stripped)
                        if isinstance(parsed, dict):
                            chat_id = parsed.get("conversation_id", "").strip()
                            if chat_id:
                                logger.debug(f"Extracted conversation ID from JSON: {chat_id}")
                                return chat_id
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from extracted value: {e}", exc_info=True)
                logger.debug(f"Extracted conversation ID as plain string: {stripped}")
                return stripped
            elif isinstance(extracted, dict):
                chat_id = extracted.get("conversation_id", "").strip()
                if chat_id:
                    logger.debug(f"Extracted conversation ID from dict: {chat_id}")
                    return chat_id
                else:
                    logger.debug("Extracted dict did not contain conversation_id.")
                    return ""
            else:
                logger.debug("Extracted value is neither str nor dict.")
                return ""
        else:
            logger.warning("No conversation ID found in tool function arguments.")
            return ""
    except Exception as e:
        logger.error(f"Error extracting chat ID with JMESPath: {e}", exc_info=True)
        return ""

def serialize_datetime(obj):
    """Serialize datetime objects to ISO format for JSON compatibility."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")
