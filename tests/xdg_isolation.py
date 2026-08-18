"""Shared XDG/HOME isolation for CLI subprocess tests.

Host ``~/.cache`` may be a broken symlink (multi-disk home layouts).
``platformdirs`` then fails on ``mkdir`` for cache (and any code that creates
``get_user_cache_dir_for_swarm() / ...`` without best-effort handling).

Always pin ``HOME`` + ``XDG_*`` (+ ``SWARM_USER_DATA_DIR``) to a writable tree
before spawning ``swarm-cli`` / ``swarm.core.swarm_cli``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

# Typer app bootstrap used by several subprocess tests.
SWARM_CLI_TYPER_BOOTSTRAP = (
    "from swarm.core.swarm_cli import app; "
    "import sys; sys.argv = ['swarm-cli'] + sys.argv[1:]; app()"
)


def pin_xdg_env(
    env: Mapping[str, str] | None = None,
    *,
    xdg_root: Path | str | None = None,
    home: Path | str | None = None,
    set_pythonpath: bool = True,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return env with writable HOME / XDG_* / SWARM_USER_DATA_DIR.

    Layouts
    -------
    * ``xdg_root`` given: ``{home,cache,config,data}/`` under that root
      (flat, preferred for hermetic CLI tests).
    * only ``home`` given: traditional ``~/.cache``, ``~/.config``,
      ``~/.local/share`` under that home (keeps expanduser-based assertions).
    * neither: temporary flat root under ``tempfile``.
    """
    e: dict[str, str] = dict(os.environ if env is None else env)

    # Redirecting HOME would hide ``pip install --user`` deps (dotenv, etc.).
    # Pin PYTHONUSERBASE to the *host* user base before HOME is rewritten.
    host_home = os.environ.get("HOME") or str(Path.home())
    e.setdefault("PYTHONUSERBASE", str(Path(host_home) / ".local"))

    # Caller already pinned (e.g. shared env across several CLI invocations):
    # only refresh PYTHONPATH / apply overrides unless an explicit layout was requested.
    already_pinned = (
        xdg_root is None
        and home is None
        and e.get("HOME")
        and e.get("XDG_CACHE_HOME")
        and e.get("SWARM_USER_DATA_DIR")
    )
    if not already_pinned:
        if xdg_root is not None:
            root = Path(xdg_root)
            h = root / "home"
            cache, config, data = root / "cache", root / "config", root / "data"
        elif home is not None:
            h = Path(home)
            cache = h / ".cache"
            config = h / ".config"
            data = h / ".local" / "share"
        else:
            root = Path(tempfile.mkdtemp(prefix="swarm-cli-xdg-"))
            h = root / "home"
            cache, config, data = root / "cache", root / "config", root / "data"

        for p in (h, cache, config, data):
            p.mkdir(parents=True, exist_ok=True)

        e["HOME"] = str(h)
        e["XDG_CACHE_HOME"] = str(cache)
        e["XDG_CONFIG_HOME"] = str(config)
        e["XDG_DATA_HOME"] = str(data)
        # Override platformdirs data root so bin/blueprints land under our tree.
        e["SWARM_USER_DATA_DIR"] = str(data / "swarm")

    if set_pythonpath:
        src = str(SRC_PATH)
        existing = e.get("PYTHONPATH", "")
        parts = [p for p in existing.split(os.pathsep) if p] if existing else []
        if src not in parts:
            e["PYTHONPATH"] = src + (os.pathsep + existing if existing else "")

    if overrides:
        e.update(dict(overrides))
    return e


def run_swarm_cli(
    *args: str,
    env: Mapping[str, str] | None = None,
    xdg_root: Path | str | None = None,
    home: Path | str | None = None,
    overrides: Mapping[str, str] | None = None,
    timeout: float = 60,
    cwd: Path | str | None = None,
    module: str | None = None,
    **run_kwargs: Any,
) -> subprocess.CompletedProcess:
    """Spawn swarm-cli with isolated XDG dirs.

    By default uses the Typer ``-c`` bootstrap (same as ``test_moa_command``).
    Pass ``module=`` (e.g. ``\"swarm.core.swarm_cli\"``) to use ``python -m``.
    """
    e = pin_xdg_env(env, xdg_root=xdg_root, home=home, overrides=overrides)
    if module:
        cmd = [sys.executable, "-m", module, *args]
    else:
        cmd = [sys.executable, "-c", SWARM_CLI_TYPER_BOOTSTRAP, *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=e,
        timeout=timeout,
        cwd=str(cwd if cwd is not None else REPO_ROOT),
        **run_kwargs,
    )
