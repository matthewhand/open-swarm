"""Honest runtime-mode banner: where *this app* is running.

Compose (or a dedicated harness) sets ``SWARM_RUNTIME`` (base compose /
Pinokio) or ``SWARM_RUNTIME_MODE`` (dev compose). Either name is accepted;
the canonical name wins when both are set. The UI banner is about the
**application** filesystem — not the browser-control provider
(Playwright-on-this-machine stays the default; sandbox/SaaS *browser* rows
stay grey TODO).

Modes
-----
- ``bare-metal`` — dedicated harness machine, no container.
- ``sandbox-home`` — compose with ``$HOME`` (or ``SWARM_SANDBOX_ROOT``) mapped.
- ``sandbox-isolated`` — compose *without* that tree mapped.

Missing or unrecognized values are ``unknown``. Never fake a green isolated
sandbox. Copy uses ``$HOME`` / ``SWARM_SANDBOX_ROOT`` placeholders only —
no real host paths, usernames, or secrets.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

ENV_RUNTIME_MODE = "SWARM_RUNTIME_MODE"
# Pinokio + docker-compose.yml announce the mode as SWARM_RUNTIME (REQ-45).
ENV_RUNTIME_MODE_ALIAS = "SWARM_RUNTIME"

MODE_BARE_METAL = "bare-metal"
MODE_SANDBOX_HOME = "sandbox-home"
MODE_SANDBOX_ISOLATED = "sandbox-isolated"
MODE_UNKNOWN = "unknown"

KNOWN_MODES = frozenset({MODE_BARE_METAL, MODE_SANDBOX_HOME, MODE_SANDBOX_ISOLATED})

# Accept a few punctuation variants; never treat a path-like string as a mode.
_ALIASES = {
    "baremetal": MODE_BARE_METAL,
    "bare_metal": MODE_BARE_METAL,
    "bare-metal": MODE_BARE_METAL,
    "sandboxhome": MODE_SANDBOX_HOME,
    "sandbox_home": MODE_SANDBOX_HOME,
    "sandbox-home": MODE_SANDBOX_HOME,
    "sandboxisolated": MODE_SANDBOX_ISOLATED,
    "sandbox_isolated": MODE_SANDBOX_ISOLATED,
    "sandbox-isolated": MODE_SANDBOX_ISOLATED,
}

TONE_WARNING = "warning"
TONE_INFO = "info"
TONE_UNKNOWN = "unknown"

_BANNERS: dict[str, dict[str, str]] = {
    MODE_BARE_METAL: {
        "tone": TONE_WARNING,
        "title": "This instance is bare metal",
        "message": (
            "This instance is a dedicated harness machine (no container). "
            "Agents that use Browser (this machine) can drive local Chrome "
            "via Playwright. Desktop/OS control stays out of scope."
        ),
    },
    MODE_SANDBOX_HOME: {
        "tone": TONE_WARNING,
        "title": "Developer sandbox with home access",
        "message": (
            "This instance is a developer sandbox with full access to $HOME "
            "(or SWARM_SANDBOX_ROOT if that root is mapped). Treat it like "
            "bare metal for files on that tree. Sandbox/SaaS browser providers "
            "are not wired."
        ),
    },
    MODE_SANDBOX_ISOLATED: {
        "tone": TONE_INFO,
        "title": "You appear to be in a sandbox env",
        "message": (
            "This instance is compose without $HOME / SWARM_SANDBOX_ROOT mapped. "
            "Isolation is the app filesystem, not a remote browser provider. "
            "Browser (this machine) is still the default Playwright target."
        ),
    },
    MODE_UNKNOWN: {
        "tone": TONE_UNKNOWN,
        "title": "Runtime mode unknown",
        "message": (
            "SWARM_RUNTIME_MODE is unset or unrecognized. This instance is not "
            "claiming to be isolated — never assume a green sandbox. Set "
            "bare-metal, sandbox-home, or sandbox-isolated."
        ),
    },
}


def normalize_runtime_mode(raw: str | None) -> str:
    """Return a known mode or ``unknown``. Never invent isolation."""
    if raw is None:
        return MODE_UNKNOWN
    token = raw.strip()
    if not token:
        return MODE_UNKNOWN
    # Paths / secrets must never be interpreted as a mode.
    if any(ch in token for ch in ("/", "\\", "$", ":", " ")):
        return MODE_UNKNOWN
    key = token.lower().replace("_", "-")
    collapsed = key.replace("-", "")
    mapped = _ALIASES.get(key) or _ALIASES.get(collapsed)
    if mapped in KNOWN_MODES:
        return mapped
    return MODE_UNKNOWN


def read_runtime_mode(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    raw = env.get(ENV_RUNTIME_MODE)
    if raw is None or not str(raw).strip():
        raw = env.get(ENV_RUNTIME_MODE_ALIAS)
    return normalize_runtime_mode(raw)


def runtime_banner(mode: str | None = None, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Structured banner payload. Safe to return over an unauthenticated GET."""
    resolved = normalize_runtime_mode(mode) if mode is not None else read_runtime_mode(environ)
    copy = _BANNERS[resolved]
    return {
        "mode": resolved,
        "known": resolved in KNOWN_MODES,
        "tone": copy["tone"],
        "title": copy["title"],
        "message": copy["message"],
        "env_var": ENV_RUNTIME_MODE,
    }
