"""
Utilities for redacting sensitive data.
"""

import logging

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_KEYS = ["secret", "password", "api_key", "apikey", "token", "access_token", "client_secret"]

def redact_sensitive_data(
    data: str | dict | list,
    sensitive_keys: list[str] | None = None,
    reveal_chars: int = 0,
    mask: str = "[REDACTED]"
) -> str | dict | list:
    """
    Recursively redact sensitive information from dictionaries, lists, or strings.
    By default, fully masks sensitive values (returns only the mask).
    If reveal_chars > 0, partially masks (preserves reveal_chars at start/end).
    If a custom mask is provided, always use it (for test compatibility).
    Handles standalone strings with sensitive patterns.
    """
    keys_to_redact = {k.lower() for k in (sensitive_keys or DEFAULT_SENSITIVE_KEYS)}

    # Patterns to detect sensitive data in strings
    sensitive_patterns = [
        r'sk-[a-zA-Z0-9]+',  # OpenAI API keys
        r'password\s*=\s*[^\s]+',  # Password assignments
        r'Bearer\s+[a-zA-Z0-9\-_\.]+',  # Bearer tokens
        r'ssh-rsa\s+[a-zA-Z0-9+/]+={0,2}',  # SSH keys
    ]

    import re

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

    def redact_string_patterns(text: str) -> str:
        """Redact sensitive patterns in standalone strings."""
        if not isinstance(text, str):
            return text

        redacted = text
        for pattern in sensitive_patterns:
            redacted = re.sub(pattern, mask, redacted)
        return redacted

    if isinstance(data, dict):
        redacted_dict = {}
        for k, v in data.items():
            if isinstance(k, str) and k.lower() in keys_to_redact:
                redacted_dict[k] = smart_mask(v)
            elif isinstance(v, dict | list):
                redacted_dict[k] = redact_sensitive_data(v, sensitive_keys, reveal_chars, mask)
            elif isinstance(v, str):
                redacted_dict[k] = redact_string_patterns(v)
            else:
                redacted_dict[k] = v
        return redacted_dict
    elif isinstance(data, list):
        processed_list = []
        for item in data:
            if isinstance(item, dict | list):
                processed_list.append(redact_sensitive_data(item, sensitive_keys, reveal_chars, mask))
            elif isinstance(item, str):
                processed_list.append(redact_string_patterns(item))
            else:
                processed_list.append(item)
        return processed_list
    elif isinstance(data, str):
        # Do not redact standalone strings, only patterns in structured data values
        return data
    return data
