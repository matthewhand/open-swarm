"""Small environment contract for live remote adapter tests."""
from __future__ import annotations

import math
import re
from urllib.parse import urlsplit

from swarm.core.remote_harness import REMOTE_IMPL_IDS


def instance_ids(env):
    extra = env.get("SWARM_LIVE_INSTANCES", "").split(",")
    ids = list(dict.fromkeys([*REMOTE_IMPL_IDS, *(x.strip().lower() for x in extra if x.strip())]))
    if any(not re.fullmatch(r"[a-z][a-z0-9_]*", x) for x in ids):
        raise ValueError("live instance names must contain only lowercase letters, digits and underscores")
    return ids


def connection(instance, env):
    """None means absent; malformed explicit settings must fail, never skip."""
    from swarm.core.remotes import default_spec

    prefix = "SWARM_LIVE_" + instance.upper() + "_"
    url = env.get(prefix + "URL", "").strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("URL must be HTTP(S), without embedded credentials, query or fragment")
    kind = env.get(prefix + "KIND", instance).strip().lower()
    if kind not in REMOTE_IMPL_IDS or kind == "herdr":
        raise ValueError("live HTTP suite requires an HTTP remote kind; Herdr needs its SSH/CLI suite")
    timeout = float(env.get(prefix + "TIMEOUT", "90"))
    if not math.isfinite(timeout) or not 1 <= timeout <= 300:
        raise ValueError("TIMEOUT must be between 1 and 300 seconds")
    spec = default_spec(kind)
    spec.id, spec.kind, spec.base_url = instance, kind, url.rstrip("/")
    # Never inherit kind credentials or a persisted config/secret store.
    spec.api_key = env.get(prefix + "API_KEY", "")
    spec.cookie = env.get(prefix + "COOKIE", "")
    spec.api_key_env = spec.session_cookie_env = ""
    spec.agent = env.get(prefix + "TARGET", "")
    spec.health_path = env.get(prefix + "HEALTH_PATH", spec.health_path)
    return spec, timeout, spec.agent


def reply_text(payload):
    """Only answer fields count: never match an echoed request or job receipt."""
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("text", "response", "output", "answer", "reply"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            return str(message.get("content") or "")
    return ""
