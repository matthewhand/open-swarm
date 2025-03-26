"""
Utilities for redacting sensitive data.
"""

import re
from typing import Union, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_KEYS = ["secret", "password", "api_key", "apikey", "token", "access_token", "client_secret"]

def redact_sensitive_data(
    data: Union[str, Dict, List],
    sensitive_keys: Optional[List[str]] = None,
    reveal_chars: int = 4,
    mask: str = "[REDACTED]"
) -> Union[str, Dict, List]:
    """
    Recursively redact sensitive information from dictionaries or lists based on keys.
    Applies partial redaction to string values associated with sensitive keys.
    Does NOT redact standalone strings.

    Args:
        data: Input data to redact (dict or list). Other types returned as is.
        sensitive_keys: List of dictionary keys to treat as sensitive. Defaults to common keys.
        reveal_chars: Number of initial/trailing characters to reveal (0 means full redaction).
        mask: String used for redaction in the middle or for full redaction of strings.

    Returns:
        Redacted data structure of the same type as input.
    """
    keys_to_redact = sensitive_keys if sensitive_keys is not None else DEFAULT_SENSITIVE_KEYS
    keys_to_redact_lower = {key.lower() for key in keys_to_redact}

    if isinstance(data, dict):
        redacted_dict = {}
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in keys_to_redact_lower:
                if isinstance(value, str):
                    val_len = len(value)
                    if reveal_chars > 0 and val_len > reveal_chars * 2:
                        redacted_dict[key] = f"{value[:reveal_chars]}{mask}{value[-reveal_chars:]}"
                    elif val_len > 0:
                         # Use the provided mask string directly for full redaction
                         redacted_dict[key] = mask
                    else:
                         redacted_dict[key] = "" # Redact empty string as empty
                else:
                    # Use specific placeholder for non-strings
                    redacted_dict[key] = "[REDACTED NON-STRING]"
            else:
                # Recursively redact nested structures if key is not sensitive
                redacted_dict[key] = redact_sensitive_data(value, keys_to_redact, reveal_chars, mask)
        return redacted_dict

    elif isinstance(data, list):
        # Recursively redact items in a list ONLY if they are dicts or lists themselves.
        processed_list = []
        for item in data:
            if isinstance(item, (dict, list)):
                processed_list.append(redact_sensitive_data(item, keys_to_redact, reveal_chars, mask))
            else:
                processed_list.append(item) # Keep non-dict/list items (like strings) unchanged
        return processed_list

    # Return data unchanged if it's not a dict or list (including standalone strings)
    return data
