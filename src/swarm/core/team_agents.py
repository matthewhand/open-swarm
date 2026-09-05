"""Available team-designer palette (REQ-20 / REQ-107).

``GET /v1/team-agents/`` lists API (blueprint dirs), CLI (catalog), and
configured remotes. No secrets. Remotes stay opt-in (empty until added).
Missing CLIs are marked ``placeholder: true``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from swarm.core.cli_catalog import catalog_names, installed_catalog_clis


def _blueprint_root() -> Path:
    try:
        from django.conf import settings

        raw = getattr(settings, "BLUEPRINT_DIRECTORY", None)
        if raw:
            return Path(raw)
    except Exception:
        pass
    return Path("src/swarm/blueprints")


def list_blueprint_ids(root: Path | None = None) -> list[str]:
    """Lightweight dir scan — no blueprint import, no live host."""
    base = root if root is not None else _blueprint_root()
    if not base.is_dir():
        return []
    names: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if any(child.glob("blueprint_*.py")):
            names.append(child.name)
    return names


def _configured_remotes() -> list[dict[str, str]]:
    try:
        from swarm.core.remotes import list_configured_remotes

        rows = []
        for spec in list_configured_remotes():
            rid = str(getattr(spec, "id", "") or "").strip()
            if not rid:
                continue
            title = str(getattr(spec, "title", "") or getattr(spec, "label", "") or rid)
            rows.append({"id": rid, "name": title})
        return rows
    except Exception:
        return []


def serialize_team_agent(
    *,
    agent_id: str,
    name: str,
    kind: str,
    source: str,
    placeholder: bool = False,
) -> dict[str, Any]:
    return {
        "id": agent_id,
        "name": name,
        "kind": kind,
        "source": source,
        "placeholder": bool(placeholder),
    }


def list_team_agents(
    *,
    blueprint_ids: list[str] | None = None,
    cli_names: list[str] | None = None,
    installed_clis: list[str] | None = None,
    remotes: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Palette rows for the team designer. Injectables keep tests host-free."""
    api_ids = blueprint_ids if blueprint_ids is not None else list_blueprint_ids()
    clis = cli_names if cli_names is not None else catalog_names()
    installed = set(installed_clis if installed_clis is not None else installed_catalog_clis())
    remote_rows = remotes if remotes is not None else _configured_remotes()

    out: list[dict[str, Any]] = []
    for name in api_ids:
        out.append(
            serialize_team_agent(
                agent_id=name,
                name=name,
                kind="api",
                source=f"blueprint:{name}",
            )
        )
    for name in clis:
        out.append(
            serialize_team_agent(
                agent_id=name,
                name=name,
                kind="cli",
                source=f"cli:{name}",
                placeholder=name not in installed,
            )
        )
    for row in remote_rows:
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue
        out.append(
            serialize_team_agent(
                agent_id=rid,
                name=str(row.get("name") or rid),
                kind="remote",
                source=f"remote:{rid}",
            )
        )
    return out
