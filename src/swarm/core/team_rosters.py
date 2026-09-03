"""Team roster composition store (REQ-20).

A **team roster** is a composition contract: a named roster of members
(API-from-blueprint, CLI, or remote harness) plus per-team openai-agents
wire toggles (handoff / as_tool).

This is **not** the Django ``/teams/`` LLM-profile alias registry.

Live vs intended
----------------
- **Live (aliases):** ``teams.json`` + ``/v1/teams/`` + Django
  ``/teams/`` admin/launcher. Schema: ``id`` / ``description`` / ``llm_profile``.
  Do not write that file from this module.
- **Intended (composition):** ``team_rosters.json`` + ``/v1/team-rosters/``.
  Schema: ``members[{id, kind, role, source}]`` + ``wires{handoff, as_tool}``.

Gate runtime (REQ-314) is not implemented here. Unwired gate means all
tools are approved — UI copy only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from swarm.core.paths import ensure_swarm_directories_exist, get_user_config_dir_for_swarm

logger = logging.getLogger(__name__)

MEMBER_KINDS = ("api", "cli", "remote")
MEMBER_ROLES = ("support", "gate", "skeptic", "default")
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


def _default_source(member_id: str, kind: str) -> str:
    if kind == "api":
        return f"blueprint:{member_id}"
    if kind == "cli":
        return f"cli:{member_id}"
    return f"placeholder:remote:{member_id}"


def normalize_member(raw: Any) -> dict[str, str]:
    """Validate and normalize one roster member. Raises ValueError."""
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

    role = str(raw.get("role") or "default").strip().lower()
    if role not in MEMBER_ROLES:
        raise ValueError(f"Member role must be one of {', '.join(MEMBER_ROLES)}.")

    source = str(raw.get("source") or "").strip() or _default_source(member_id, kind)
    return {"id": member_id, "kind": kind, "role": role, "source": source}


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
    members_in = raw.get("members") or []
    if not isinstance(members_in, list):
        raise ValueError("members must be an array.")
    members = [normalize_member(m) for m in members_in]
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


def reset_team_rosters() -> None:
    """Clear the in-memory cache (tests). Does not write disk unless save is called."""
    global _roster_registry
    _roster_registry = None


# ---------------------------------------------------------------------------
# Available-agent catalog (API / CLI / remote). Remotes and missing CLIs are
# placeholders — never registered as Blueprint classes.
# ---------------------------------------------------------------------------

PLACEHOLDER_REMOTE_AGENTS: tuple[dict[str, str], ...] = (
    {
        "id": "acp",
        "name": "ACP harness",
        "kind": "remote",
        "source": "placeholder:remote:acp",
        "note": "Placeholder — remote harness API is not in this tree.",
    },
    {
        "id": "ssh-remote",
        "name": "SSH remote",
        "kind": "remote",
        "source": "placeholder:remote:ssh-remote",
        "note": "Placeholder — remote harness API is not in this tree.",
    },
)

PLACEHOLDER_CLI_AGENTS: tuple[dict[str, str], ...] = (
    {"id": "grok", "name": "grok", "kind": "cli", "source": "placeholder:cli:grok"},
    {"id": "claude", "name": "claude", "kind": "cli", "source": "placeholder:cli:claude"},
    {"id": "gemini", "name": "gemini", "kind": "cli", "source": "placeholder:cli:gemini"},
)


def _blueprint_agents() -> list[dict[str, Any]]:
    """API members come from discovered blueprints (not remotes/CLIs)."""
    from django.conf import settings as dj_settings

    from swarm.core.blueprint_discovery import (
        apply_blueprint_aliases,
        discover_blueprints,
        merge_community_blueprints,
    )

    discovered = discover_blueprints(dj_settings.BLUEPRINT_DIRECTORY)
    discovered = merge_community_blueprints(
        discovered, getattr(dj_settings, "BLUEPRINT_EXTRA_DIRS", None)
    )
    discovered = apply_blueprint_aliases(discovered)
    agents: list[dict[str, Any]] = []
    if not isinstance(discovered, dict):
        return agents
    for blueprint_id, info in discovered.items():
        meta = info.get("metadata", {}) if isinstance(info, dict) else {}
        name = meta.get("name") or blueprint_id
        agents.append(
            {
                "id": blueprint_id,
                "name": name,
                "kind": "api",
                "source": f"blueprint:{blueprint_id}",
                "description": meta.get("description") or "",
                "placeholder": False,
            }
        )
    agents.sort(key=lambda a: str(a["name"]).lower())
    return agents


def _cli_agents() -> list[dict[str, Any]]:
    try:
        from swarm.core import cli_catalog

        names = list(cli_catalog.catalog_names())
    except Exception:
        logger.exception("CLI catalog unavailable; using CLI placeholders.")
        return [
            {**entry, "description": "", "placeholder": True, "note": "Placeholder — CLI catalog unavailable."}
            for entry in PLACEHOLDER_CLI_AGENTS
        ]
    if not names:
        return [
            {**entry, "description": "", "placeholder": True, "note": "Placeholder — no CLIs in catalog."}
            for entry in PLACEHOLDER_CLI_AGENTS
        ]
    return [
        {
            "id": name,
            "name": name,
            "kind": "cli",
            "source": f"cli:{name}",
            "description": "",
            "placeholder": False,
        }
        for name in names
    ]


def _remote_agents() -> list[dict[str, Any]]:
    return [
        {
            **entry,
            "description": entry.get("note", ""),
            "placeholder": True,
        }
        for entry in PLACEHOLDER_REMOTE_AGENTS
    ]


def list_available_team_agents() -> list[dict[str, Any]]:
    """Compose the available-agent palette. Failures degrade to placeholders."""
    agents: list[dict[str, Any]] = []
    try:
        agents.extend(_blueprint_agents())
    except Exception:
        logger.exception("Blueprint discovery failed for team-agent catalog.")
    try:
        agents.extend(_cli_agents())
    except Exception:
        logger.exception("CLI catalog failed for team-agent catalog.")
        agents.extend(
            {
                **entry,
                "description": "",
                "placeholder": True,
                "note": "Placeholder — CLI catalog unavailable.",
            }
            for entry in PLACEHOLDER_CLI_AGENTS
        )
    agents.extend(_remote_agents())
    return agents
