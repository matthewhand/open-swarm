"""Team roster composition store (REQ-20 / REQ-28).

A **team roster** is a composition contract: a named roster of members
plus per-team openai-agents wire toggles (handoff / as_tool).

Member shape (``team_rosters`` / ``agent_team`` members)::

    {id, kind: api|cli|remote|team|herdr, role, source}

``kind=team`` also carries ``team_id`` (the nested roster). Parent talks to
that child team as **one member** (send-to-all on the child), not every
grandchild — see ``docs/TEAM_ISOLATION.md``.

This is **not** the Django ``/teams/`` LLM-profile alias registry
(``teams.json``). Never write that file from this module.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from swarm.core.agent_roles import CANONICAL_ROLES, normalize_agent_role
from swarm.core.paths import ensure_swarm_directories_exist, get_user_config_dir_for_swarm

logger = logging.getLogger(__name__)

MEMBER_KINDS = ("api", "cli", "remote", "team", "herdr")
DEFAULT_WIRES = {"handoff": True, "as_tool": True}

# In-memory cache. Isolated from swarm.views.utils._dynamic_registry (teams.json).
_roster_registry: dict[str, dict[str, Any]] | None = None


def team_rosters_path() -> Path:
    """XDG path for the composition store. Never ``teams.json``."""
    ensure_swarm_directories_exist()
    return get_user_config_dir_for_swarm() / "team_rosters.json"


def slugify_roster_name(name: str) -> str:
    """Slugify a roster name (same character rules as the alias admin)."""
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def _default_source(member_id: str, kind: str, team_id: str | None = None) -> str:
    if kind == "api":
        return f"blueprint:{member_id}"
    if kind == "cli":
        return f"cli:{member_id}"
    if kind == "team":
        return f"team:{team_id or member_id}"
    if kind == "herdr":
        return f"herdr:{member_id}"
    return f"placeholder:remote:{member_id}"


def normalize_member(raw: Any) -> dict[str, str]:
    """Validate and normalize one roster / agent_team member. Raises ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("Each member must be an object.")
    member_id = str(raw.get("id") or "").strip()
    if not member_id:
        raise ValueError("Member id is required.")
    if len(member_id) > 64:
        raise ValueError("Member id too long (max 64).")

    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in MEMBER_KINDS:
        raise ValueError(f"Member kind must be one of {', '.join(MEMBER_KINDS)}.")

    role = normalize_agent_role(raw.get("role") or "default")
    if role not in CANONICAL_ROLES:
        raise ValueError(f"Member role must be one of {', '.join(CANONICAL_ROLES)}.")

    team_id = str(raw.get("team_id") or "").strip()
    if kind == "team":
        team_id = team_id or member_id
    elif team_id:
        # Non-team members may still record a home team; keep it if present.
        pass
    else:
        team_id = ""

    source = str(raw.get("source") or "").strip() or _default_source(member_id, kind, team_id or None)
    member = {"id": member_id, "kind": kind, "role": role, "source": source}
    if team_id:
        member["team_id"] = team_id
    return member


def normalize_wires(raw: Any) -> dict[str, bool]:
    """Per-team wire toggles. Missing keys default on."""
    wires = dict(DEFAULT_WIRES)
    if raw is None:
        return wires
    if not isinstance(raw, dict):
        raise ValueError("wires must be an object.")
    for key in ("handoff", "as_tool"):
        if key in raw:
            val = raw[key]
            if not isinstance(val, bool):
                raise ValueError(f"wires.{key} must be a boolean.")
            wires[key] = val
    return wires


def normalize_roster(raw: dict[str, Any], *, roster_id: str | None = None) -> dict[str, Any]:
    """Normalize a roster document. Raises ValueError on bad input."""
    rid = (roster_id or raw.get("id") or "").strip()
    if not rid:
        raise ValueError("Roster id is required.")
    name = str(raw.get("name") or rid).strip() or rid
    members_in = raw.get("members") or raw.get("agent_team") or []
    if not isinstance(members_in, list):
        raise ValueError("members must be an array.")
    members = [normalize_member(m) for m in members_in]
    for member in members:
        if member.get("kind") == "team" and member.get("team_id") == rid:
            raise ValueError("A team cannot nest itself as a member.")
    return {
        "id": rid,
        "name": name,
        "members": members,
        "wires": normalize_wires(raw.get("wires")),
    }


def serialize_roster(entry: dict[str, Any]) -> dict[str, Any]:
    """Public JSON shape (OpenAPI / SPA)."""
    normalized = normalize_roster(entry, roster_id=entry.get("id"))
    return {
        "id": normalized["id"],
        "object": "team_roster",
        "name": normalized["name"],
        "members": normalized["members"],
        "wires": normalized["wires"],
    }


def load_team_rosters() -> dict[str, dict[str, Any]]:
    """Load the in-memory roster registry from ``team_rosters.json``."""
    global _roster_registry
    if _roster_registry is not None:
        return _roster_registry
    try:
        path = team_rosters_path()
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            if not raw.strip():
                _roster_registry = {}
            else:
                parsed = json.loads(raw) or {}
                if not isinstance(parsed, dict):
                    logger.error("team_rosters.json root must be an object; using empty registry.")
                    _roster_registry = {}
                else:
                    _roster_registry = parsed
        else:
            _roster_registry = {}
    except Exception:
        logger.exception("Failed to load team_rosters.json; using empty registry.")
        _roster_registry = {}
    return _roster_registry


def save_team_rosters() -> None:
    """Persist the in-memory roster registry to ``team_rosters.json``.

    Never writes ``teams.json``.
    """
    path = team_rosters_path()
    if path.name != "team_rosters.json":
        raise RuntimeError("Refusing to persist team rosters to a non-roster path.")
    try:
        path.write_text(json.dumps(_roster_registry or {}, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to persist team rosters to %s", path)
        raise


def get_roster(roster_id: str) -> dict[str, Any] | None:
    return load_team_rosters().get(roster_id)


def upsert_roster(roster: dict[str, Any]) -> dict[str, Any]:
    """Insert or replace a roster and persist. Returns the stored document."""
    normalized = normalize_roster(roster)
    reg = load_team_rosters()
    reg[normalized["id"]] = {
        "id": normalized["id"],
        "name": normalized["name"],
        "members": normalized["members"],
        "wires": normalized["wires"],
    }
    save_team_rosters()
    return reg[normalized["id"]]


def delete_roster(roster_id: str) -> bool:
    """Remove a roster. Returns True if it existed."""
    reg = load_team_rosters()
    if roster_id not in reg:
        return False
    reg.pop(roster_id, None)
    save_team_rosters()
    return True


def reset_team_rosters(initial: dict[str, dict[str, Any]] | None = None) -> None:
    """Replace the in-memory cache (tests). Does not write disk unless save is called."""
    global _roster_registry
    _roster_registry = None if initial is None else dict(initial)


def iter_normalized_rosters(
    rosters: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return ``{id: normalized_roster}`` from an in-memory map or the store."""
    raw = rosters if rosters is not None else load_team_rosters()
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for rid, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        try:
            out[str(rid)] = normalize_roster(entry, roster_id=str(entry.get("id") or rid))
        except ValueError:
            logger.warning("Skipping invalid roster %s", rid)
    return out
