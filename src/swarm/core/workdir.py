"""Confine per-request ``workdir`` / ``cwd`` under a workspaces root.

API clients (and blueprints that honor ``params.workdir``) must not point
WorkspaceTools or sandbox-bypassing CLI agents at arbitrary filesystem paths.
Paths resolve under ``SWARM_WORKSPACES_DIR`` / ``WORKSPACES_DIR`` or the XDG
user data ``workspaces/`` directory. Absolute paths outside that root are
rejected unless ``ALLOW_UNRESTRICTED_WORKDIR=true`` (local power-user escape).

Auto-minted ``run-*`` directories are marked and may be deleted via
:func:`cleanup_run_workdir` after the request finishes.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from swarm.core.paths import get_user_data_dir_for_swarm

ENV_WORKSPACES_DIR = "SWARM_WORKSPACES_DIR"
ENV_WORKSPACES_DIR_ALT = "WORKSPACES_DIR"
ENV_ALLOW_UNRESTRICTED = "ALLOW_UNRESTRICTED_WORKDIR"
ENV_RUN_WORKDIR_MAX_AGE_DAYS = "SWARM_RUN_WORKDIR_MAX_AGE_DAYS"

#: Marker written into auto-minted run directories (cleanup requires this or name match).
AUTO_RUN_MARKER = ".swarm-auto-run"
#: Default name prefix for auto-minted dirs (``run-<12 hex>``).
DEFAULT_RUN_PREFIX = "run-"
#: Default age before opportunistic prune of leftover auto run dirs.
DEFAULT_PRUNE_DAYS = 7.0

_AUTO_RUN_NAME = re.compile(r"^run-[0-9a-f]{12}$")
_logger = logging.getLogger(__name__)


class WorkdirEscapeError(ValueError):
    """Raised when a client workdir resolves outside the workspaces root."""


def unrestricted_workdir_allowed() -> bool:
    """True when power users explicitly allow arbitrary absolute workdirs."""
    return os.environ.get(ENV_ALLOW_UNRESTRICTED, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def get_workspaces_dir() -> Path:
    """Return the configured workspaces root (created on demand by callers).

    Precedence: ``SWARM_WORKSPACES_DIR`` → ``WORKSPACES_DIR`` →
    ``<user data dir>/workspaces``.
    """
    override = os.environ.get(ENV_WORKSPACES_DIR) or os.environ.get(ENV_WORKSPACES_DIR_ALT)
    if override and override.strip():
        return Path(override).expanduser()
    return get_user_data_dir_for_swarm() / "workspaces"


def _is_under(child: Path, root: Path) -> bool:
    try:
        if child == root:
            return True
        return child.is_relative_to(root)
    except (OSError, ValueError):
        return False


def _is_blank(raw: str | os.PathLike[str] | None) -> bool:
    return raw is None or not str(raw).strip()


def is_auto_workdir_request(raw: str | os.PathLike[str] | None) -> bool:
    """True when *raw* would mint a fresh per-run directory."""
    return _is_blank(raw)


def _mark_auto_run(path: Path) -> None:
    marker = path / AUTO_RUN_MARKER
    try:
        marker.write_text(f"{time.time():.3f}\n", encoding="utf-8")
    except OSError as e:
        _logger.debug("failed to mark auto run workdir %s: %s", path, e)


def _looks_like_auto_run_dir(path: Path) -> bool:
    if (path / AUTO_RUN_MARKER).is_file():
        return True
    return bool(_AUTO_RUN_NAME.match(path.name))


def is_auto_run_workdir(path: str | os.PathLike[str] | Path) -> bool:
    """True if *path* is under the workspaces root and looks auto-minted."""
    root = get_workspaces_dir().expanduser().resolve()
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        return False
    if resolved == root or not _is_under(resolved, root):
        return False
    if not resolved.is_dir():
        return False
    return _looks_like_auto_run_dir(resolved)


def cleanup_run_workdir(path: str | os.PathLike[str] | Path | None) -> bool:
    """Delete an auto-minted run workdir.

    Returns True only when the path was removed. Refuses paths outside the
    workspaces root, the root itself, and directories that do not look like
    auto-created ``run-*`` dirs (marker file or ``run-<12 hex>`` name).
    Never deletes user-provided workspace paths.
    """
    if path is None:
        return False
    root = get_workspaces_dir().expanduser().resolve()
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        return False
    if resolved == root or not _is_under(resolved, root):
        return False
    if not resolved.is_dir() or not _looks_like_auto_run_dir(resolved):
        return False
    try:
        shutil.rmtree(resolved)
        return True
    except OSError as e:
        _logger.warning("failed to cleanup run workdir %s: %s", resolved, e)
        return False


def _prune_max_age_days() -> float:
    raw = os.environ.get(ENV_RUN_WORKDIR_MAX_AGE_DAYS, "").strip()
    if not raw:
        return DEFAULT_PRUNE_DAYS
    try:
        days = float(raw)
    except ValueError:
        return DEFAULT_PRUNE_DAYS
    return days if days > 0 else DEFAULT_PRUNE_DAYS


def prune_stale_run_workdirs(
    *,
    max_age_days: float | None = None,
    root: Path | None = None,
) -> int:
    """Best-effort delete of leftover auto ``run-*`` dirs older than *max_age_days*.

    Only inspects immediate children of the workspaces root. Returns the number
    of directories removed. Errors are swallowed.
    """
    age_days = DEFAULT_PRUNE_DAYS if max_age_days is None else float(max_age_days)
    if age_days <= 0:
        return 0
    base = (root or get_workspaces_dir()).expanduser().resolve()
    if not base.is_dir():
        return 0
    cutoff = time.time() - (age_days * 86400.0)
    removed = 0
    try:
        children = list(base.iterdir())
    except OSError:
        return 0
    for child in children:
        try:
            if not child.is_dir() or not _looks_like_auto_run_dir(child):
                continue
            if not _is_under(child.resolve(), base):
                continue
            mtime = child.stat().st_mtime
            if mtime > cutoff:
                continue
            shutil.rmtree(child)
            removed += 1
        except OSError:
            continue
    return removed


def resolve_confined_workdir(
    raw: str | os.PathLike[str] | None,
    *,
    create: bool = True,
    prefix: str = DEFAULT_RUN_PREFIX,
    prune_stale: bool = True,
) -> Path:
    """Resolve *raw* to a workdir under the workspaces root.

    * ``None`` / blank → a fresh per-run directory under the root.
    * Relative path → joined under the root (``..`` escapes rejected).
    * Absolute path under the root → accepted.
    * Absolute path outside the root → ``WorkdirEscapeError`` unless
      ``ALLOW_UNRESTRICTED_WORKDIR`` is set (then the path is used as-is).

    When *create* is true the directory (and parents) are created. Auto-minted
    dirs are marked with :data:`AUTO_RUN_MARKER`. When minting, a small
    opportunistic prune of stale ``run-*`` dirs may run (*prune_stale*).
    """
    root = get_workspaces_dir().expanduser().resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)

    text = None if raw is None else str(raw).strip()
    if not text:
        if prune_stale:
            try:
                prune_stale_run_workdirs(max_age_days=_prune_max_age_days(), root=root)
            except Exception:  # pragma: no cover - never fail resolve on prune
                _logger.debug("stale run workdir prune failed", exc_info=True)
        path = root / f"{prefix}{uuid.uuid4().hex[:12]}"
        if create:
            path.mkdir(parents=True, exist_ok=True)
            _mark_auto_run(path)
        return path.resolve()

    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        try:
            resolved = candidate.resolve()
        except OSError as e:
            raise WorkdirEscapeError(f"invalid workdir: {text!r}") from e
        if _is_under(resolved, root):
            if create:
                resolved.mkdir(parents=True, exist_ok=True)
            return resolved
        if unrestricted_workdir_allowed():
            if create:
                resolved.mkdir(parents=True, exist_ok=True)
            return resolved
        raise WorkdirEscapeError(
            f"workdir {text!r} is outside the workspaces root ({root}). "
            f"Use a relative path under that root, set {ENV_WORKSPACES_DIR}, "
            f"or set {ENV_ALLOW_UNRESTRICTED}=true for unrestricted local use."
        )

    # Relative: join under root; resolve and re-check (blocks .. escapes).
    joined = (root / candidate).resolve()
    if not _is_under(joined, root):
        raise WorkdirEscapeError(
            f"workdir {text!r} escapes the workspaces root ({root})."
        )
    if create:
        joined.mkdir(parents=True, exist_ok=True)
    return joined


def default_run_workdir(*, prefix: str = DEFAULT_RUN_PREFIX) -> Path:
    """Create and return a fresh per-run workdir under the workspaces root."""
    return resolve_confined_workdir(None, create=True, prefix=prefix)


def make_temp_workdir(*, prefix: str = DEFAULT_RUN_PREFIX) -> Path:
    """``mkdtemp`` under the workspaces root (same confinement guarantees)."""
    root = get_workspaces_dir().expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=str(root))).resolve()
    _mark_auto_run(path)
    return path
