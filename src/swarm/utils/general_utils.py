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

# Define default JMESPath expressions here - split for individual processing
DEFAULT_CHAT_ID_PATHS_LIST = [
    "metadata.channelInfo.channelId",
    "metadata.userInfo.userId",
    "`json_parse(messages[-1].tool_calls[-1].function.arguments).chat_id`" # This path requires custom handling or a registered json_parse function
]

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
    colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m", "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m", "white": "\033[97m", }
    reset = "\033[0m"
    return colors.get(color, "") + text + reset

def _search_and_process_jmespath(expression: str, payload: dict) -> str:
    """Helper to search JMESPath and process the result into a string ID."""
    chat_id = ""
    try:
        # Handle the specific case of json_parse manually for now
        if 'json_parse' in expression and 'messages[-1].tool_calls[-1].function.arguments' in expression and '.chat_id' in expression:
            logger.debug(f"Attempting manual handling for json_parse expression: {expression}")
            try:
                # Extract the arguments string first using a simpler path
                args_str = jmespath.search('messages[-1].tool_calls[-1].function.arguments', payload)
                if isinstance(args_str, str):
                    args_dict = json.loads(args_str)
                    extracted_value = args_dict.get('chat_id')
                    # Proceed with processing extracted_value below
                else:
                    logger.debug("Arguments for json_parse path not found or not a string.")
                    return ""
            except (json.JSONDecodeError, jmespath.exceptions.JMESPathError, IndexError, TypeError, KeyError) as e:
                logger.debug(f"Manual handling of json_parse failed: {e}")
                return ""
        else:
            # Evaluate standard JMESPath expression
            extracted_value = jmespath.search(expression, payload)

        # Process the extracted value (whether from standard path or manual json_parse)
        if extracted_value is not None:
            if isinstance(extracted_value, str):
                stripped_value = extracted_value.strip()
                if stripped_value:
                     # Check if the result is the literal expression itself (contains backticks) - indicates failure for custom functions
                     if '`' in stripped_value or 'json_parse' in stripped_value:
                          logger.debug(f"JMESPath expression '{expression}' likely returned literal or unevaluated function string: '{stripped_value}'. Treating as not found.")
                          return ""

                     # Attempt to parse if it looks like JSON, otherwise treat as plain ID
                     try:
                         if stripped_value.startswith('{') and stripped_value.endswith('}'):
                             parsed_json = json.loads(stripped_value)
                             if isinstance(parsed_json, dict):
                                 possible_keys = ["conversation_id", "chat_id", "channelId", "sessionId", "id"]
                                 for key in possible_keys:
                                      id_val = parsed_json.get(key)
                                      if id_val and isinstance(id_val, str):
                                           chat_id = id_val.strip()
                                           if chat_id: return chat_id
                                 return "" # Parsed dict, but no ID key
                             else: return "" # Parsed, but not dict
                         else:
                              chat_id = stripped_value # Treat as plain ID
                     except json.JSONDecodeError:
                         chat_id = stripped_value # Treat as plain ID if parsing fails but didn't look like JSON dict
                     except Exception as e:
                          logger.error(f"Unexpected error processing potential JSON string from '{expression}': {e}")
                          return ""
                else: return "" # Empty string extracted
            elif isinstance(extracted_value, dict):
                 possible_keys = ["conversation_id", "chat_id", "channelId", "sessionId", "id"]
                 for key in possible_keys:
                      id_val = extracted_value.get(key)
                      if id_val and isinstance(id_val, str):
                           chat_id = id_val.strip()
                           if chat_id: return chat_id
                 return "" # Dict found, but no ID key
            elif isinstance(extracted_value, (int, float, bool)):
                 return str(extracted_value) # Convert simple types
            else:
                 logger.warning(f"Extracted value via '{expression}' is of unsupported type: {type(extracted_value)}. Returning empty string.")
                 return ""
        else: return "" # JMESPath returned None

    except jmespath.exceptions.JMESPathError as jmes_err:
         logger.debug(f"JMESPath expression '{expression}' failed: {jmes_err}")
         return ""
    except Exception as e:
        logger.error(f"Unexpected error evaluating JMESPath '{expression}': {e}", exc_info=True)
        return ""

    return str(chat_id) if chat_id is not None else ""


def extract_chat_id(payload: dict) -> str:
    """
    Extract chat ID using JMESPath defined by STATEFUL_CHAT_ID_PATH env var,
    or fallback to trying a list of hardcoded default paths.
    Returns the first valid chat ID found, or empty string ("").
    """
    path_expr_env = os.getenv("STATEFUL_CHAT_ID_PATH", "").strip()
    paths_to_try: List[str] = []
    source = ""

    if path_expr_env:
        paths_to_try = [p.strip() for p in path_expr_env.split('||') if p.strip()]
        source = "environment variable"
        logger.debug(f"Using chat ID paths from {source}: {paths_to_try}")
    else:
        paths_to_try = DEFAULT_CHAT_ID_PATHS_LIST
        source = "hardcoded defaults"
        logger.debug(f"STATEFUL_CHAT_ID_PATH not set, using {source}: {paths_to_try}")

    if not paths_to_try:
        logger.warning(f"No chat ID JMESPath expressions found from {source}.")
        return ""

    for expression in paths_to_try:
        logger.debug(f"Trying JMESPath expression: {expression}")
        chat_id = _search_and_process_jmespath(expression, payload)
        if chat_id: # If a non-empty string ID was found
            return chat_id

    logger.debug("No chat ID found after trying all expressions.")
    return ""

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime): return obj.isoformat()
    elif isinstance(obj, str): return obj
    raise TypeError(f"Type {type(obj)} not serializable")

def custom_json_dumps(obj, **kwargs):
    defaults = {'default': serialize_datetime}; defaults.update(kwargs)
    return json.dumps(obj, **defaults)

