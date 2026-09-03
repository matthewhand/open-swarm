"""First-class agent roles for visual distinction and team wiring.

Canonical roles (REQ-7 / REQ-9):

* ``default`` — ordinary worker / coordinator
* ``support`` — Support agent (REQ-7 introduces the seat; this module names it)
* ``gate`` — tool-call classifier (alias ``tool_gate``)
* ``skeptic`` — post-run reviewer that may hand findings back to the original agent

Sidepane class names (Support should reuse these, not invent a parallel set):

* ``os-agent-role-<role>`` on the row (e.g. ``os-agent-role-gate``)
* ``data-role="<role>"`` on the row and the accent dot
* ``os-agent-role-badge`` for the optional label chip
"""

from __future__ import annotations

from typing import Any, Iterable

ROLE_DEFAULT = "default"
ROLE_SUPPORT = "support"
ROLE_GATE = "gate"
ROLE_SKEPTIC = "skeptic"

# User-facing / config aliases → canonical role.
ROLE_ALIASES: dict[str, str] = {
    "default": ROLE_DEFAULT,
    "worker": ROLE_DEFAULT,
    "agent": ROLE_DEFAULT,
    "coordinator": ROLE_DEFAULT,
    "support": ROLE_SUPPORT,
    "helper": ROLE_SUPPORT,
    "gate": ROLE_GATE,
    "tool_gate": ROLE_GATE,
    "tool-gate": ROLE_GATE,
    "toolgate": ROLE_GATE,
    "skeptic": ROLE_SKEPTIC,
    "reviewer": ROLE_SKEPTIC,
}

CANONICAL_ROLES: tuple[str, ...] = (
    ROLE_DEFAULT,
    ROLE_SUPPORT,
    ROLE_GATE,
    ROLE_SKEPTIC,
)

# CSS contract for the AGENTS sidepane (Django + SPA).
ROLE_CSS_CLASS_PREFIX = "os-agent-role-"
ROLE_CSS_CLASSES: dict[str, str] = {
    role: f"{ROLE_CSS_CLASS_PREFIX}{role}" for role in CANONICAL_ROLES
}


def normalize_agent_role(value: Any) -> str:
    """Map a free-text / alias role to a canonical visual/wiring role.

    Unknown values (e.g. Team Creator specializations like ``Writer``) become
    ``default`` so they never accidentally enable gate or skeptic wiring.
    """
    if value is None:
        return ROLE_DEFAULT
    key = str(value).strip().lower().replace(" ", "_")
    if not key:
        return ROLE_DEFAULT
    return ROLE_ALIASES.get(key, ROLE_DEFAULT)


def role_css_class(role: Any) -> str:
    """Return ``os-agent-role-<canonical>`` for a role value."""
    return ROLE_CSS_CLASSES[normalize_agent_role(role)]


def role_from_agent(agent: Any) -> str:
    """Read ``role`` from an openai-agents Agent, spec dict, or attribute bag."""
    if agent is None:
        return ROLE_DEFAULT
    if isinstance(agent, dict):
        return normalize_agent_role(agent.get("role"))
    return normalize_agent_role(getattr(agent, "role", None))


def attach_role(agent: Any, role: Any) -> Any:
    """Stamp a canonical ``role`` attribute on an Agent (or any object)."""
    canonical = normalize_agent_role(role)
    try:
        agent.role = canonical
    except Exception:
        pass
    return agent


def _agent_name(agent: Any, fallback: str | None = None) -> str | None:
    if isinstance(agent, dict):
        name = agent.get("name")
    else:
        name = getattr(agent, "name", None)
    if name:
        return str(name)
    return fallback


def find_role_agent(agents: Any, role: str) -> Any | None:
    """Return the first agent/spec whose role matches *role*, or ``None``.

    *agents* may be a ``{name: agent}`` map or a list of specs/agents.
    Unwired (no match) is a normal outcome — callers must fail-open.
    """
    want = normalize_agent_role(role)
    if want == ROLE_DEFAULT:
        return None
    if agents is None:
        return None
    items: Iterable[tuple[str | None, Any]]
    if isinstance(agents, dict):
        items = agents.items()
    else:
        items = ((_agent_name(a), a) for a in agents)
    for _name, agent in items:
        if role_from_agent(agent) == want:
            return agent
    return None


def find_role_name(agents: Any, role: str) -> str | None:
    """Name of the first agent wired as *role*, or ``None`` if unwired."""
    agent = find_role_agent(agents, role)
    if agent is None:
        return None
    return _agent_name(agent)


def normalize_roster(agents: Any) -> list[dict[str, str]]:
    """``[{name, role}, ...]`` for API / sidepane consumers."""
    roster: list[dict[str, str]] = []
    if agents is None:
        return roster
    if isinstance(agents, dict):
        iterable = agents.items()
    else:
        pairs: list[tuple[str | None, Any]] = []
        for i, item in enumerate(agents):
            if isinstance(item, str):
                pairs.append((item, {"name": item, "role": ROLE_DEFAULT}))
            else:
                pairs.append((_agent_name(item, str(i)), item))
        iterable = pairs
    for name, agent in iterable:
        if not name or str(name).startswith("_"):
            continue
        roster.append({
            "name": str(name),
            "role": role_from_agent(agent),
        })
    return roster


def blueprint_role_fields(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Serialize role + roster + wiring names for ``/v1/blueprints/``.

    Blueprint-level ``role`` is explicit metadata (Support / a dedicated gate
    blueprint). Member wiring lives on ``agents[]`` plus ``gate_agent`` /
    ``skeptic_agent``. A team that merely *contains* a gate does not change the
    team's own sidepane role unless ``metadata.role`` says so.
    """
    meta = meta or {}
    raw_agents = meta.get("agents")
    roster = normalize_roster(raw_agents) if raw_agents else []
    # Allow roster entries that are already {name, role} dicts with extra keys.
    if raw_agents and not roster and isinstance(raw_agents, list):
        roster = [
            {"name": str(item), "role": ROLE_DEFAULT}
            for item in raw_agents
            if item
        ]
    role = normalize_agent_role(meta.get("role"))
    gate = meta.get("gate_agent") or find_role_name(roster, ROLE_GATE)
    skeptic = meta.get("skeptic_agent") or find_role_name(roster, ROLE_SKEPTIC)
    return {
        "role": role,
        "agents": roster,
        "gate_agent": gate,
        "skeptic_agent": skeptic,
    }
