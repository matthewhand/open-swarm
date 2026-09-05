"""First-class agent roles for rail look and team wiring.

Canonical roles:

* ``default`` — ordinary worker
* ``support`` — Support seat (REQ-7). Teal badge.
* ``gate`` — tool-call classifier (alias ``tool_gate``). Amber badge.
* ``skeptic`` — post-run reviewer. Violet badge.
* ``chief_of_staff`` — talks to any team (aliases ``cos``, ``chief``). Ice-steel badge.
* ``suggestions`` — quick-select chips after a turn (REQ-85). Sage badge.

Sidepane class names (reuse these; do not invent a parallel set):

* ``os-agent-role-badge`` is the only role colour (chip + ``os-agent-role-<role>``)
* ``data-role="<role>"`` may appear on the row for identification
* Rows have no role fill, left-border accent, or outline (REQ-67)

REQ-28: Chief of Staff keeps a distinct **badge** colour — not support / gate /
skeptic. REQ-67 removed role row chrome. Hover-edit (REQ-25) can later target
this role's blueprint; this module at least names the badge contract.
"""

from __future__ import annotations

from typing import Any, Iterable

ROLE_DEFAULT = "default"
ROLE_SUPPORT = "support"
ROLE_GATE = "gate"
ROLE_SKEPTIC = "skeptic"
ROLE_CHIEF_OF_STAFF = "chief_of_staff"
ROLE_SUGGESTIONS = "suggestions"

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
    "chief_of_staff": ROLE_CHIEF_OF_STAFF,
    "chief-of-staff": ROLE_CHIEF_OF_STAFF,
    "chiefofstaff": ROLE_CHIEF_OF_STAFF,
    "cos": ROLE_CHIEF_OF_STAFF,
    "chief": ROLE_CHIEF_OF_STAFF,
    "suggestions": ROLE_SUGGESTIONS,
    "suggestion": ROLE_SUGGESTIONS,
    "suggest": ROLE_SUGGESTIONS,
}

CANONICAL_ROLES: tuple[str, ...] = (
    ROLE_DEFAULT,
    ROLE_SUPPORT,
    ROLE_GATE,
    ROLE_SKEPTIC,
    ROLE_CHIEF_OF_STAFF,
    ROLE_SUGGESTIONS,
)

ROLE_BADGE_LABELS: dict[str, str] = {
    ROLE_DEFAULT: "",
    ROLE_SUPPORT: "Support",
    ROLE_GATE: "Gate",
    ROLE_SKEPTIC: "Skeptic",
    ROLE_CHIEF_OF_STAFF: "CoS",
    ROLE_SUGGESTIONS: "Suggest",
}

# CSS contract for the AGENTS sidepane badge (Django + SPA). REQ-67: not on the row.
ROLE_CSS_CLASS_PREFIX = "os-agent-role-"
ROLE_CSS_CLASSES: dict[str, str] = {
    role: f"{ROLE_CSS_CLASS_PREFIX}{role}" for role in CANONICAL_ROLES
}


def normalize_agent_role(value: Any) -> str:
    """Map a free-text / alias role to a canonical visual/wiring role.

    Unknown values become ``default`` so they never accidentally enable
    gate, skeptic, or chief-of-staff wiring.
    """
    if value is None:
        return ROLE_DEFAULT
    key = str(value).strip().lower().replace(" ", "_")
    if not key:
        return ROLE_DEFAULT
    return ROLE_ALIASES.get(key, ROLE_DEFAULT)


def is_chief_of_staff(role: Any) -> bool:
    """True when *role* is ``chief_of_staff`` (including ``cos`` / ``chief``)."""
    return normalize_agent_role(role) == ROLE_CHIEF_OF_STAFF


def role_css_class(role: Any) -> str:
    """Return ``os-agent-role-<canonical>`` for a role value."""
    return ROLE_CSS_CLASSES[normalize_agent_role(role)]


def role_badge_label(role: Any) -> str:
    """Short chip label (``CoS``, ``Gate``, …). Empty for ``default``."""
    return ROLE_BADGE_LABELS.get(normalize_agent_role(role), "")


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
        name = agent.get("name") or agent.get("id")
    else:
        name = getattr(agent, "name", None) or getattr(agent, "id", None)
    if name:
        return str(name)
    return fallback


def find_role_agent(agents: Any, role: str) -> Any | None:
    """Return the first agent/spec whose role matches *role*, or ``None``."""
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

    Blueprint-level ``role`` is explicit metadata (Support / gate / CoS).
    Member wiring lives on ``agents[]`` plus ``gate_agent`` / ``skeptic_agent``
    / ``suggestions_agent``.
    """
    meta = meta or {}
    raw_agents = meta.get("agents")
    roster = normalize_roster(raw_agents) if raw_agents else []
    if raw_agents and not roster and isinstance(raw_agents, list):
        roster = [
            {"name": str(item), "role": ROLE_DEFAULT}
            for item in raw_agents
            if item
        ]
    role = normalize_agent_role(meta.get("role"))
    gate = meta.get("gate_agent") or find_role_name(roster, ROLE_GATE)
    skeptic = meta.get("skeptic_agent") or find_role_name(roster, ROLE_SKEPTIC)
    cos = meta.get("chief_of_staff_agent") or find_role_name(roster, ROLE_CHIEF_OF_STAFF)
    suggestions = meta.get("suggestions_agent") or find_role_name(roster, ROLE_SUGGESTIONS)
    return {
        "role": role,
        "agents": roster,
        "gate_agent": gate,
        "skeptic_agent": skeptic,
        "chief_of_staff_agent": cos,
        "suggestions_agent": suggestions,
    }
