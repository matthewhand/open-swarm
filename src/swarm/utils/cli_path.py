"""Host ``PATH`` widening for CLI discovery and MCP stdio children.

This module stays import-light (stdlib only). ``swarm.core.cli_catalog``
re-exports these names, but MCP env construction must import them from here
so building a child environment does not load the catalog, Django, or the
openai-agents SDK.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def npm_shim_argv(executable: str) -> list[str] | None:
    """Resolve a standard Windows npm shim without invoking cmd.exe.

    npm installs POSIX, .cmd and PowerShell launchers side by side. Windows
    cannot CreateProcess the POSIX file; a command shell would reinterpret
    untrusted prompt arguments. Read only the generated .cmd target instead.
    Custom scripts are not interpreted, and targets must stay in node_modules.
    """
    path = Path(executable)
    if path.suffix.lower() == ".exe":
        return None
    native = path.with_suffix(".exe")
    if native.is_file():
        return [str(native)]
    shim = path if path.suffix.lower() == ".cmd" else path.with_suffix(".cmd")
    try:
        text = shim.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if "SET dp0=%~dp0" not in text or "CALL :find_dp0" not in text:
        return None
    match = re.search(r'"%dp0%[\\/]node_modules[\\/]([^"\r\n]+\.(?:js|mjs|cjs|exe))"', text, re.I)
    if not match:
        return None
    root = (shim.parent / "node_modules").resolve()
    target = root.joinpath(*match.group(1).replace("\\", "/").split("/")).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    if target.suffix.lower() == ".exe":
        return [str(target)]
    node = shim.parent / "node.exe"
    runtime = str(node) if node.is_file() else shutil.which("node.exe")
    return [runtime, str(target)] if runtime else None

# User-local bins Daphne often misses when started with PATH=/usr/bin:/bin.
_EXTRA_BIN_REL = (
    (".local", "bin"),
    ("bin",),
    (".grok", "bin"),
    (".opencode", "bin"),
    (".npm-global", "bin"),
    (".local", "share", "pnpm"),
    # #1175: hermes's launcher execs `python` from its venv bin; the venv's
    # python symlink resolves into ~/.local/share/uv (mounted ro for CLI
    # discovery). Without this dir on PATH the launcher dies with
    # "venv/bin/python: No such file or directory".
    (".hermes", "hermes-agent", "venv", "bin"),
)

# Image-local bins preferred over host mounts when running in a Linux
# container (#1718): Docker Desktop on Windows bind-mounts PE / exit-126
# shims into $HOME/.local/bin that discovery would otherwise win.
_IMAGE_BIN_DIRS = ("/usr/local/bin",)


def in_linux_container() -> bool:
    """True when this process is a Linux container (e.g. Docker ``/.dockerenv``)."""
    if os.name != "posix":
        return False
    return os.path.exists("/.dockerenv")


def is_foreign_windows_binary(path: str) -> bool:
    """True when *path* is a Windows PE (``MZ``) on a non-Windows host.

    #1718: host-mounted ``.exe`` / PE files on Docker Desktop are discoverable
    but exit 126 (ENOEXEC) inside the Linux container.
    """
    if not path or os.name == "nt":
        return False
    try:
        with open(path, "rb") as fh:
            magic = fh.read(2)
    except OSError:
        return False
    return magic == b"MZ"


def is_runnable_cli_binary(path: str) -> bool:
    """True when *path* is a file the current OS can plausibly exec."""
    if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
        return False
    if is_foreign_windows_binary(path):
        return False
    return True


def extra_cli_path_dirs() -> list[str]:
    """User and nvm bin dirs that commonly hold grok/agy/pi/opencode.

    ``SWARM_CLI_PATH_DIRS`` (``os.pathsep``-joined) extends the scan - the
    deployment knob for containerised runs whose host bin mounts differ
    (#716/#717). Configured dirs come first and must exist.

    Node CLIs are frequently installed twice: an old, globally-pinned copy in
    ``~/.npm-global/bin`` (or another user bin) and the current release under
    ``~/.nvm/versions/node/<latest>/bin``. Scanning the static dirs first wins
    the stale copy (e.g. pi 0.74.2 rejecting a modern ``--approve``). The nvm
    newest-version dirs are therefore scanned *before* the static dirs; both
    still come after ``SWARM_CLI_PATH_DIRS``.

    #1718: inside a Linux container, ``/usr/local/bin`` (baked image CLIs such
    as opencode) is scanned immediately after ``SWARM_CLI_PATH_DIRS`` and
    *before* host-mounted ``$HOME`` bins, so Windows Docker dogfood does not
    prefer a PE / exit-126 shim over the in-image Linux binary.
    """
    # Prefer HOME when set so tests and container mounts that pin HOME
    # (Docker Desktop) are honored; expanduser("~") ignores HOME on Windows.
    home = os.environ.get("HOME") or os.path.expanduser("~")
    dirs: list[str] = []
    configured = os.environ.get("SWARM_CLI_PATH_DIRS", "")
    for d in configured.split(os.pathsep):
        if d.strip() and os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    image_first = in_linux_container()
    if image_first:
        for path in _IMAGE_BIN_DIRS:
            if os.path.isdir(path) and path not in dirs:
                dirs.append(path)
    nvm = os.path.join(home, ".nvm", "versions", "node")
    if os.path.isdir(nvm):
        for ver in sorted(os.listdir(nvm), reverse=True):
            path = os.path.join(nvm, ver, "bin")
            if os.path.isdir(path) and path not in dirs:
                dirs.append(path)
    for parts in _EXTRA_BIN_REL:
        path = os.path.join(home, *parts)
        if os.path.isdir(path) and path not in dirs:
            dirs.append(path)
    if not image_first:
        for path in _IMAGE_BIN_DIRS:
            if os.path.isdir(path) and path not in dirs:
                dirs.append(path)
    return dirs


def host_cli_path(current: str | None = None) -> str:
    """``PATH`` with extra user bin dirs prepended (deduped)."""
    current = os.environ.get("PATH", "") if current is None else current
    parts: list[str] = []
    seen: set[str] = set()
    for d in [*extra_cli_path_dirs(), *current.split(os.pathsep)]:
        if d and d not in seen:
            seen.add(d)
            parts.append(d)
    return os.pathsep.join(parts)
