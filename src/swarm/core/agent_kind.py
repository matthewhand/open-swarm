"""Classify chat agents as API, CLI, or remote (REQ-49).

API-agent threads are owned by Open Swarm and may be edited in place.
CLI and remote sessions are owned outside swarm — no edit.
"""

from __future__ import annotations

from typing import Literal

AgentKind = Literal["api", "cli", "remote"]

_VALID_KINDS = frozenset({"api", "cli", "remote"})


def classify_agent_kind(
    raw: str | None,
    *,
    explicit: str | None = None,
) -> AgentKind:
    """Return ``api``, ``cli``, or ``remote`` for an agent id / source.

    Explicit kind (from a roster or fixture) wins when it is one of the
    three values. Otherwise source-style prefixes are used:

    * ``cli:<name>`` → cli
    * ``remote:<name>`` / ``placeholder:remote:…`` → remote
    * everything else (including API blueprints such as ``cli_agent``) → api
    """
    if explicit in _VALID_KINDS:
        return explicit  # type: ignore[return-value]
    text = (raw or "").strip().lower()
    if text.startswith("cli:"):
        return "cli"
    if text.startswith("remote:") or text.startswith("placeholder:remote:"):
        return "remote"
    return "api"


def can_edit_agent_messages(
    raw: str | None,
    *,
    explicit: str | None = None,
) -> bool:
    """True only for API-agent threads (REQ-49)."""
    return classify_agent_kind(raw, explicit=explicit) == "api"
