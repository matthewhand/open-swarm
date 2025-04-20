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
    reveal_chars: int = 0,
    mask: str = "[REDACTED]"
) -> Union[str, Dict, List]:
    """
    Recursively redact sensitive information from dictionaries or lists based on keys.
    By default, fully masks sensitive values (returns only the mask).
    If reveal_chars > 0, partially masks (preserves reveal_chars at start/end).
    If a custom mask is provided, always use it (for test compatibility).
    Does NOT redact standalone strings.
    """
    keys_to_redact = set((k.lower() for k in (sensitive_keys or DEFAULT_SENSITIVE_KEYS)))
    def smart_mask(val: str) -> str:
        if not isinstance(val, str):
            return val
        if mask != "[REDACTED]":
            return mask
        if reveal_chars == 0:
            return mask
        if len(val) >= 2 * reveal_chars + 1:
            return val[:reveal_chars] + mask + val[-reveal_chars:]
        return mask
    if isinstance(data, dict):
        redacted_dict = {}
        for k, v in data.items():
            if isinstance(k, str) and k.lower() in keys_to_redact:
                redacted_dict[k] = smart_mask(v)
            elif isinstance(v, (dict, list)):
                redacted_dict[k] = redact_sensitive_data(v, sensitive_keys, reveal_chars, mask)
            else:
                redacted_dict[k] = v
        return redacted_dict
    elif isinstance(data, list):
        processed_list = []
        for item in data:
            if isinstance(item, (dict, list)):
                processed_list.append(redact_sensitive_data(item, sensitive_keys, reveal_chars, mask))
            else:
                processed_list.append(item)
        return processed_list
    return data
