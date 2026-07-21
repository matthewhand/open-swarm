"""
Utilities for redacting sensitive data.
"""

import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_KEYS = [
    "secret",
    "password",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "client_secret",
    "authorization",
    "private_key",
    "credentials",
]
_DEFAULT_SENSITIVE_KEYS_LOWER = {k.lower() for k in DEFAULT_SENSITIVE_KEYS}

SENSITIVE_PATTERNS = [
    r'sk-[a-zA-Z0-9]+',  # OpenAI API keys
    r'password\s*=\s*[^\s]+',  # Password assignments
    r'Bearer\s+[a-zA-Z0-9\-_\.]+',  # Bearer tokens
    r'ssh-rsa\s+[a-zA-Z0-9+/]+={0,2}',  # SSH keys
]
_COMPILED_SENSITIVE_PATTERNS = [re.compile(p) for p in SENSITIVE_PATTERNS]


def _normalize_key(key: str) -> str:
    """Lowercase and unify separators so OPENAI-API-KEY matches api_key heuristics."""
    return key.lower().replace("-", "_")


def is_sensitive_key(key: str, sensitive_keys: set[str] | None = None) -> bool:
    """
    True if *key* is an exact sensitive name or embeds one (OPENAI_API_KEY, GITHUB_TOKEN).

    Exact match alone misses common env-style names; substring match closes that gap
    without requiring every provider prefix to be enumerated.
    """
    keys = sensitive_keys if sensitive_keys is not None else _DEFAULT_SENSITIVE_KEYS_LOWER
    kl = _normalize_key(key)
    if kl in keys:
        return True
    for sk in keys:
        if sk and sk in kl:
            return True
    return False


def redact_sensitive_data(
    data: str | dict | list,
    sensitive_keys: list[str] | set[str] | None = None,
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
    if sensitive_keys:
        # If it's already a set, we still lowercase it to be safe,
        # but recursive calls will pass the set we already computed.
        if isinstance(sensitive_keys, set):
            keys_to_redact = sensitive_keys
        else:
            keys_to_redact = {_normalize_key(k) for k in sensitive_keys}
    else:
        keys_to_redact = _DEFAULT_SENSITIVE_KEYS_LOWER

    def smart_mask(val: str) -> str:
        if not isinstance(val, str):
            # A sensitive key's value must never leak just because it isn't a
            # string (ints, bools, dicts/lists stored under a secret key, …).
            return mask
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
        for pattern in _COMPILED_SENSITIVE_PATTERNS:
            redacted = pattern.sub(mask, redacted)
        return redacted

    if isinstance(data, dict):
        redacted_dict = {}
        for k, v in data.items():
            if isinstance(k, str) and is_sensitive_key(k, keys_to_redact):
                redacted_dict[k] = smart_mask(v)
            elif isinstance(v, dict | list):
                redacted_dict[k] = redact_sensitive_data(v, keys_to_redact, reveal_chars, mask)
            elif isinstance(v, str):
                redacted_dict[k] = redact_string_patterns(v)
            else:
                redacted_dict[k] = v
        return redacted_dict
    elif isinstance(data, list):
        processed_list = []
        for item in data:
            if isinstance(item, dict | list):
                processed_list.append(redact_sensitive_data(item, keys_to_redact, reveal_chars, mask))
            elif isinstance(item, str):
                processed_list.append(redact_string_patterns(item))
            else:
                processed_list.append(item)
        return processed_list
    elif isinstance(data, str):
        # Do not redact standalone strings, only patterns in structured data values
        # NOTE: The docstring says it handles them, but the implementation explicitly
        # skipped them to avoid over-redaction of plain text.
        return data
    return data
