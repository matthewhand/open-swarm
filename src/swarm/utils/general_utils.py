"""
General utility functions for the Swarm framework.
"""
import os
import logging
import jmespath
import json
import datetime
from typing import Optional, List, Dict, Any

from swarm.utils.logger_setup import setup_logger

# Initialize logger for this module
logger = setup_logger(__name__)

def find_project_root(current_path: str, marker: str = ".git") -> str:
    """Find project root by looking for a marker (.git)."""
    current_path = os.path.abspath(current_path)
    while True:
        if os.path.exists(os.path.join(current_path, marker)):
            return current_path
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            break
        current_path = parent_path
    logger.warning(f"Project root marker '{marker}' not found starting from {current_path}.")
    raise FileNotFoundError(f"Project root with marker '{marker}' not found.")

def color_text(text: str, color: str = "white") -> str:
    """Color text using ANSI escape codes."""
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
        "white": "\033[97m",
    }
    reset = "\033[0m"
    return colors.get(color, "") + text + reset

def extract_chat_id(payload: dict) -> str:
    """
    Extract chat ID using JMESPath defined by STATEFUL_CHAT_ID_PATH.
    Handles cases where the extracted value is a JSON string containing the ID.
    Returns empty string on failure or if not found.
    """
    chat_id = ""
    path_expr = ""
    try:
        path_expr = os.getenv("STATEFUL_CHAT_ID_PATH", "").strip()
        if not path_expr:
            logger.debug("STATEFUL_CHAT_ID_PATH environment variable not set or empty.")
            return ""

        logger.debug(f"Attempting to extract chat ID using JMESPath: {path_expr}")
        extracted_value = jmespath.search(path_expr, payload)

        if extracted_value:
            if isinstance(extracted_value, str):
                stripped_value = extracted_value.strip()
                if stripped_value:
                    try:
                        # Always try to parse non-empty strings
                        parsed_json = json.loads(stripped_value)
                        # If it parsed successfully
                        if isinstance(parsed_json, dict):
                            possible_keys = ["conversation_id", "chat_id", "channelId", "sessionId", "id"]
                            for key in possible_keys:
                                 id_val = parsed_json.get(key)
                                 if id_val and isinstance(id_val, str):
                                      chat_id = id_val.strip()
                                      if chat_id:
                                           logger.debug(f"Extracted chat ID '{chat_id}' from key '{key}' in parsed JSON string.")
                                           return chat_id
                            logger.debug(f"Parsed JSON string (dict), but known ID keys not found.")
                            return "" # Key not found
                        else:
                            logger.debug(f"Parsed JSON string is not a dictionary.")
                            return "" # Not a dict, can't get ID
                    except json.JSONDecodeError:
                        # Failed to parse: Treat as plain string *unless* it looked like JSON
                        # Relaxed check: Only check start character
                        if stripped_value.startswith(('{', '[')):
                            logger.debug(f"Value '{stripped_value}' looked like JSON but failed to parse. Returning empty string.")
                            return "" # Explicitly return "" for malformed JSON
                        else:
                            # Didn't look like JSON, treat as plain string ID
                            logger.debug(f"Extracted chat ID as plain string: {stripped_value}")
                            chat_id = stripped_value
                else: return "" # Empty string extracted

            elif isinstance(extracted_value, dict):
                possible_keys = ["conversation_id", "chat_id", "channelId", "sessionId", "id"]
                for key in possible_keys:
                     id_val = extracted_value.get(key)
                     if id_val and isinstance(id_val, str):
                          chat_id = id_val.strip()
                          if chat_id:
                               logger.debug(f"Extracted chat ID '{chat_id}' from key '{key}' in dictionary.")
                               return chat_id
                logger.debug("Extracted dictionary did not contain a known chat ID key.")
                return ""
            else:
                logger.warning(f"Extracted value is of unexpected type: {type(extracted_value)}.")
                return ""
        else:
            logger.debug(f"JMESPath expression '{path_expr}' returned no result.")
            return ""

    except jmespath.exceptions.ParseError as jmes_err:
         logger.error(f"Invalid JMESPath expression '{path_expr}': {jmes_err}")
         return ""
    except Exception as e:
        logger.error(f"Error extracting chat ID with JMESPath expression '{path_expr}': {e}", exc_info=True)
        return ""

    return str(chat_id) if chat_id is not None else ""


def serialize_datetime(obj):
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, str):
         return obj
    raise TypeError(f"Type {type(obj)} not serializable by this custom serializer")

def custom_json_dumps(obj, **kwargs):
    """Wrapper for json.dumps using the custom datetime serializer."""
    defaults = {'default': serialize_datetime}
    defaults.update(kwargs)
    return json.dumps(obj, **defaults)
