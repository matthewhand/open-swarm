"""Unified dotenv loading for Open Swarm.

Precedence:
  1. Process env already set at call time (systemd ``Environment=`` /
     ``EnvironmentFile=``, shell exports) — never overwritten.
  2. ``~/.config/swarm/.env`` (or ``$XDG_CONFIG_HOME/swarm/.env``) — primary
     operator secrets; wins over project checkout ``.env``.
  3. Project-root ``.env`` — dev fallback for keys not in (1) or (2).

Call ``load_swarm_dotenv()`` early from manage.py, settings, wsgi, and CLI.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


def xdg_swarm_env_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "swarm" / ".env"


def project_env_path(project_root: Path | None = None) -> Path:
    if project_root is not None:
        return Path(project_root) / ".env"
    here = Path(__file__).resolve()
    # src/swarm/utils/dotenv_load.py → parents[3] == repo root (…/open-swarm-mcp)
    return here.parents[3] / ".env"


def load_swarm_dotenv(project_root: Path | None = None) -> list[str]:
    """Load project then XDG dotenv with unit/shell env winning.

    Returns a list of human-readable status strings for diagnostics.
    """
    loaded: list[str] = []
    preexisting = set(os.environ.keys())

    proj = project_env_path(project_root)
    if proj.is_file():
        load_dotenv(dotenv_path=proj, override=False)
        loaded.append(str(proj.resolve()))

    xdg = xdg_swarm_env_path()
    if xdg.is_file():
        applied = 0
        for key, value in (dotenv_values(xdg) or {}).items():
            if value is None or key in preexisting:
                continue
            # XDG wins over project-only keys; never stomps unit/shell.
            os.environ[key] = value
            applied += 1
        loaded.append(f"{xdg.resolve()} (+{applied} keys)")

    return loaded
