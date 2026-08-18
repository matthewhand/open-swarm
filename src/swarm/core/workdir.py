"""Confine per-request ``workdir`` / ``cwd`` under a workspaces root.

API clients (and blueprints that honor ``params.workdir``) must not point
WorkspaceTools or sandbox-bypassing CLI agents at arbitrary filesystem paths.
Paths resolve under ``SWARM_WORKSPACES_DIR`` / ``WORKSPACES_DIR`` or the XDG
user data ``workspaces/`` directory. Absolute paths outside that root are
rejected unless ``ALLOW_UNRESTRICTED_WORKDIR=true`` (local power-user escape).
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from swarm.core.paths import get_user_data_dir_for_swarm

ENV_WORKSPACES_DIR = "SWARM_WORKSPACES_DIR"
ENV_WORKSPACES_DIR_ALT = "WORKSPACES_DIR"
ENV_ALLOW_UNRESTRICTED = "ALLOW_UNRESTRICTED_WORKDIR"


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


def resolve_confined_workdir(
    raw: str | os.PathLike[str] | None,
    *,
    create: bool = True,
    prefix: str = "run-",
) -> Path:
    """Resolve *raw* to a workdir under the workspaces root.

    * ``None`` / blank → a fresh per-run directory under the root.
    * Relative path → joined under the root (``..`` escapes rejected).
    * Absolute path under the root → accepted.
    * Absolute path outside the root → ``WorkdirEscapeError`` unless
      ``ALLOW_UNRESTRICTED_WORKDIR`` is set (then the path is used as-is).

    When *create* is true the directory (and parents) are created.
    """
    root = get_workspaces_dir().expanduser().resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)

    text = None if raw is None else str(raw).strip()
    if not text:
        path = root / f"{prefix}{uuid.uuid4().hex[:12]}"
        if create:
            path.mkdir(parents=True, exist_ok=True)
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


def default_run_workdir(*, prefix: str = "run-") -> Path:
    """Create and return a fresh per-run workdir under the workspaces root."""
    return resolve_confined_workdir(None, create=True, prefix=prefix)


# tempfile kept imported for callers that want mkdtemp under root explicitly
def make_temp_workdir(*, prefix: str = "run-") -> Path:
    """``mkdtemp`` under the workspaces root (same confinement guarantees)."""
    root = get_workspaces_dir().expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(root))).resolve()
