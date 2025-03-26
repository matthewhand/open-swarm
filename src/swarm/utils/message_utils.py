"""
Utility functions for processing chat messages in the Swarm framework.
"""

import logging
import json # Added import

logger = logging.getLogger(__name__)

def filter_duplicate_system_messages(messages):
    """Remove duplicate system messages, keeping only the first occurrence."""
    filtered = []
    system_found = False
    for msg in messages:
         # Ensure msg is a dictionary and has a 'role' key
        if isinstance(msg, dict) and "role" in msg:
            if msg["role"] == "system":
                if not system_found:
                    filtered.append(msg)
                    system_found = True
                # Else: skip subsequent system messages
            else:
                filtered.append(msg)
        elif isinstance(msg, dict): # Handle dicts without 'role' if necessary
             # Keep dicts without roles based on previous behavior? Or filter?
             # Let's keep them for now, consistent with test_filter_mixed_valid_invalid expectation
             logger.warning(f"Message dictionary missing 'role' key: {msg}")
             filtered.append(msg)
        else:
             logger.warning(f"Skipping non-dictionary item in messages list: {type(msg)}")
             # Skip non-dict items

    return filtered

def filter_messages(messages):
    """Filter out messages with empty/None content or only whitespace, unless they have tool_calls."""
    result = []
    if not isinstance(messages, list):
         logger.error(f"filter_messages received non-list input: {type(messages)}")
         return []

    for msg in messages:
        if not isinstance(msg, dict):
            logger.warning(f"Skipping non-dictionary item in messages list: {type(msg)}")
            continue

        content = msg.get('content')
        tool_calls = msg.get('tool_calls')

        # Keep message if it has non-whitespace content OR has non-empty tool_calls
        has_valid_content = content is not None and isinstance(content, str) and content.strip() != ""
        has_tool_calls = tool_calls is not None and isinstance(tool_calls, list) and len(tool_calls) > 0

        if has_valid_content or has_tool_calls:
            result.append(msg)
        else:
             logger.debug(f"Filtering out message due to empty/None/whitespace content and no tool calls: {msg}")

    return result


def update_null_content(input_data):
    """
    Replace 'content: None' with 'content: ""' in a message dictionary or list of dictionaries.
    Does NOT add the 'content' key if it's missing.
    """
    if isinstance(input_data, dict):
        # Process a single message dictionary
        # Check if 'content' key exists AND its value is None
        if 'content' in input_data and input_data['content'] is None:
            input_data['content'] = ""
            logger.debug(f"Updated 'content: None' to 'content: \"\"' in dict: {input_data.get('role', 'N/A')}")
        return input_data
    elif isinstance(input_data, list):
        # Process a list of messages (modify in-place or create new list)
        # Creating new list to avoid modifying original list unexpectedly
        processed_list = []
        for msg in input_data:
            if isinstance(msg, dict):
                 # Create a copy to modify
                 new_msg = msg.copy()
                 if 'content' in new_msg and new_msg['content'] is None:
                     new_msg['content'] = ""
                     logger.debug(f"Updated 'content: None' to 'content: \"\"' in list item: {new_msg.get('role', 'N/A')}")
                 processed_list.append(new_msg)
            else:
                 logger.warning(f"Skipping non-dictionary item during null content update: {type(msg)}")
                 processed_list.append(msg) # Append non-dict item unchanged
        return processed_list
    else:
         # Return other types unchanged
         logger.warning(f"update_null_content received unexpected type: {type(input_data)}. Returning unchanged.")
         return input_data

# redact_sensitive_data is now centralized in swarm.utils.redact
