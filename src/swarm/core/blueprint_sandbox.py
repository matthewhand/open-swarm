"""AST-based safety gate for user/community blueprint source.

Bundled blueprints under ``src/swarm/blueprints`` are trusted and skip this
gate.  Modules discovered from the user blueprints directory (or other extra
roots) are scanned before ``exec_module`` so obvious escape hatches never run.

Operators can opt out with ``SWARM_USER_BLUEPRINT_SANDBOX=false``.
"""

from __future__ import annotations

import ast
import os
from typing import Final

# Top-level modules that must never appear in user blueprint imports.
# Focused on process/network escape and code-loading primitives.
BANNED_MODULES: Final[frozenset[str]] = frozenset(
    {
        "subprocess",
        "ctypes",
        "socket",
        "pickle",
        "importlib",
        "multiprocessing",
        "shutil",
        "pty",
        "fcntl",
        "signal",
        "code",
        "codeop",
    }
)

# Builtins / free names that must not be called.
BANNED_CALL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "breakpoint",
    }
)

# Attribute names that indicate reflection / dynamic import abuse.
BANNED_ATTR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "__import__",
        "__builtins__",
        "__loader__",
        "__spec__",
        "__subclasses__",
        "__globals__",
        "__code__",
        "__reduce__",
        "__reduce_ex__",
    }
)

# Modes that turn open() into a write/mutate call.
_WRITE_OPEN_MODES: Final[frozenset[str]] = frozenset(
    {
        "w",
        "a",
        "x",
        "w+",
        "a+",
        "x+",
        "wb",
        "ab",
        "xb",
        "w+b",
        "a+b",
        "x+b",
        "wb+",
        "ab+",
        "xb+",
        "wt",
        "at",
        "xt",
        "w+t",
        "a+t",
        "x+t",
    }
)

# pathlib.Path (and similar) mutation methods.  Importing Path remains allowed
# for read-only use (read_text, exists, iterdir, …).  Attr-based so both
# ``Path(...).write_text`` and ``p.write_text`` are caught.  Do not include
# generic names like ``replace`` (str.replace) or ``remove`` (list.remove).
_BANNED_PATH_MUTATION_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "write_text",
        "write_bytes",
        "unlink",
        "touch",
        "mkdir",
        "rmdir",
        "chmod",
        "symlink_to",
        "hardlink_to",
    }
)

# os.* process / FS mutation APIs (owner must be the name ``os``).
_BANNED_OS_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "system",
        "popen",
        "exec",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "fork",
        "forkpty",
        "remove",
        "unlink",
        "rename",
        "renames",
        "replace",
        "mkdir",
        "makedirs",
        "rmdir",
        "removedirs",
        "chmod",
        "chown",
        "lchmod",
        "lchown",
        "symlink",
        "link",
        "truncate",
    }
)

# Path / PurePath constructors used to detect ``Path(...).rename`` style calls.
_PATH_CTOR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "Path",
        "PurePath",
        "PosixPath",
        "WindowsPath",
        "PurePosixPath",
        "PureWindowsPath",
    }
)

# Path methods whose names collide with common non-FS APIs (e.g. str.replace).
_BANNED_PATH_OWNED_MUTATION_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "rename",
        "replace",
    }
)


def sandbox_enabled() -> bool:
    """Return whether the user-blueprint sandbox gate is active (default on)."""
    raw = os.getenv("SWARM_USER_BLUEPRINT_SANDBOX", "true")
    return raw.strip().lower() in ("1", "true", "yes", "y", "t", "on")


def assert_safe_blueprint_source(source: str) -> None:
    """Raise ``ValueError`` if *source* uses banned constructs.

    This is a static AST check — not a full sandbox.  It blocks common
    escape hatches stronger than a plain substring ban list.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Blueprint source has invalid syntax: {exc}") from exc

    for node in ast.walk(tree):
        _check_node(node)


def _check_node(node: ast.AST) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            _reject_module(alias.name, node)
        return

    if isinstance(node, ast.ImportFrom):
        if node.module:
            _reject_module(node.module, node)
            # ``from os import remove`` / ``from os.path import ...`` — only
            # block dangerous names pulled directly from ``os``.
            mod_root = node.module.split(".", 1)[0]
            if mod_root == "os" and node.module == "os":
                for alias in node.names:
                    if alias.name in _BANNED_OS_ATTRS:
                        raise ValueError(
                            f"Banned import of os.{alias.name} in user blueprint "
                            f"(line {getattr(node, 'lineno', '?')})"
                        )
        for alias in node.names:
            # ``from . import subprocess`` when module is relative/None
            root = alias.name.split(".", 1)[0]
            if root in BANNED_MODULES:
                raise ValueError(
                    f"Banned import of {alias.name!r} in user blueprint "
                    f"(line {getattr(node, 'lineno', '?')})"
                )
        return

    if isinstance(node, ast.Call):
        _check_call(node)
        return

    if isinstance(node, ast.Attribute):
        if node.attr in BANNED_ATTR_NAMES:
            raise ValueError(
                f"Banned attribute access {node.attr!r} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )
        return

    if isinstance(node, ast.Name):
        # Block aliasing / bare references to dangerous builtins / interpreter state.
        if node.id in (
            "eval", "exec", "compile", "__import__", "__builtins__",
        ) and isinstance(node.ctx, (ast.Load, ast.Store)):
            raise ValueError(
                f"Banned name {node.id!r} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )


def _reject_module(module_name: str, node: ast.AST) -> None:
    root = (module_name or "").split(".", 1)[0]
    if root in BANNED_MODULES:
        raise ValueError(
            f"Banned import of {root!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )


def _call_func_name(node: ast.Call) -> str | None:
    """Best-effort name of the callable (``eval``, ``os.system``, …)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_path_ctor_receiver(func: ast.Attribute) -> bool:
    """True when the attribute is clearly on a Path/PurePath constructor result."""
    val = func.value
    if isinstance(val, ast.Name) and val.id in _PATH_CTOR_NAMES:
        return True
    if isinstance(val, ast.Attribute) and val.attr in _PATH_CTOR_NAMES:
        return True
    if isinstance(val, ast.Call):
        ctor = _call_func_name(val)
        if ctor in _PATH_CTOR_NAMES:
            return True
    return False


def _check_call(node: ast.Call) -> None:
    name = _call_func_name(node)
    if name is None:
        return

    if name in BANNED_CALL_NAMES:
        raise ValueError(
            f"Banned call to {name!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )

    # Namespace reflection (getattr/setattr with constant attrs is common and allowed)
    if name in ("vars", "globals", "locals"):
        raise ValueError(
            f"Banned reflective call {name!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )

    if name == "open":
        _check_open_call(node)
        return

    if isinstance(node.func, ast.Attribute):
        attr = node.func.attr

        # os.system / os.remove / os.rename / … (before generic Path attr bans
        # so messages stay ``os.unlink`` rather than bare ``unlink``)
        if isinstance(node.func.value, ast.Name):
            owner = node.func.value.id
            if owner == "os" and attr in _BANNED_OS_ATTRS:
                raise ValueError(
                    f"Banned call to os.{attr} in user blueprint "
                    f"(line {getattr(node, 'lineno', '?')})"
                )

        # pathlib.Path mutation (unique method names — safe to match by attr)
        if attr in _BANNED_PATH_MUTATION_ATTRS:
            raise ValueError(
                f"Banned filesystem mutation call {attr!r} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )

        # Path.rename / Path.replace — only when receiver is clearly a Path ctor
        # (avoid false positives on str.replace / custom rename helpers)
        if attr in _BANNED_PATH_OWNED_MUTATION_ATTRS and _is_path_ctor_receiver(
            node.func
        ):
            raise ValueError(
                f"Banned Path.{attr} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )


def _check_open_call(node: ast.Call) -> None:
    """Reject ``open(..., 'w')`` / keyword mode= write variants when detectable."""
    mode: str | None = None
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(
        node.args[1].value, str
    ):
        mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(
            kw.value.value, str
        ):
            mode = kw.value.value
    if mode is None:
        # open(path) defaults to read; dynamic mode left to runtime policy
        return
    if mode in _WRITE_OPEN_MODES or any(c in mode for c in ("w", "a", "x")):
        raise ValueError(
            f"Banned open() with write mode {mode!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )
