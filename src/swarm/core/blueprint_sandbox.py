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
        # Block aliasing / bare references to dangerous builtins.
        if node.id in ("eval", "exec", "compile", "__import__") and isinstance(
            node.ctx, (ast.Load, ast.Store)
        ):
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


def _check_call(node: ast.Call) -> None:
    name = _call_func_name(node)
    if name is None:
        return

    if name in BANNED_CALL_NAMES:
        raise ValueError(
            f"Banned call to {name!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )

    # getattr/setattr/delattr and namespace reflection
    if name in ("getattr", "setattr", "delattr", "vars", "globals", "locals"):
        raise ValueError(
            f"Banned reflective call {name!r} in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )

    if name == "open":
        _check_open_call(node)
        return

    # os.system / os.popen / os.exec*
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        owner = node.func.value.id
        attr = node.func.attr
        if owner == "os" and attr in (
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
        ):
            raise ValueError(
                f"Banned call to os.{attr} in user blueprint "
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
