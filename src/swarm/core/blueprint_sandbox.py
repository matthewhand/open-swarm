"""AST-based safety gate for user/community blueprint source.

Bundled blueprints under ``src/swarm/blueprints`` are trusted and skip this
gate.  Modules discovered from the user blueprints directory (or other extra
roots) are scanned before ``exec_module`` so obvious escape hatches never run.

Operators can opt out with ``SWARM_USER_BLUEPRINT_SANDBOX=false``.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Final

# Top-level modules that must never appear in user blueprint imports.
# Focused on process/network escape and code-loading primitives.
# Root match covers submodules (e.g. ``urllib`` bans ``urllib.request``).
BANNED_MODULES: Final[frozenset[str]] = frozenset(
    {
        "subprocess",
        "ctypes",
        "socket",
        "pickle",
        "importlib",
        # run_path / run_module execute arbitrary files — same class as importlib
        "runpy",
        "multiprocessing",
        "shutil",
        "pty",
        "fcntl",
        "signal",
        "code",
        "codeop",
        # Platform modules backing ``os`` (``posix.system`` / ``nt`` twin of os.*)
        "posix",
        "nt",
        "_posixsubprocess",
        # HTTP / network clients (SSRF / secret exfil)
        "urllib",
        "urllib3",
        "http",
        "httpx",
        "requests",
        "aiohttp",
        "httplib2",
        "httpcore",
        "websockets",
        "websocket",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "xmlrpc",
        "pycurl",
    }
)

# Builtins / free names that must not be called.
# Also includes distinctive asyncio process/network escapes so both
# ``asyncio.create_subprocess_exec`` and ``from asyncio import …`` call sites
# are caught via ``_call_func_name`` (attr or bare name).
BANNED_CALL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "breakpoint",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "open_connection",
        "open_unix_connection",
        "start_server",
        "start_unix_server",
        # AbstractEventLoop process APIs (``loop.subprocess_exec``)
        "subprocess_exec",
        "subprocess_shell",
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
# ``open`` / ``write`` / ``writev`` / ``pwrite`` / ``fdopen`` block low-level
# write escapes that bypass the builtin ``open(..., 'w')`` ban.
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
        "open",
        "write",
        "writev",
        "pwrite",
        "fdopen",
    }
)

# asyncio.* process / network escapes (owner must be the name ``asyncio``).
# Overlaps BANNED_CALL_NAMES for ``asyncio.X``; also covers less-distinctive
# names (``create_connection``) that are only banned on the asyncio module.
_BANNED_ASYNCIO_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "create_subprocess_exec",
        "create_subprocess_shell",
        "open_connection",
        "open_unix_connection",
        "start_server",
        "start_unix_server",
        "create_connection",
        "create_server",
        "create_unix_connection",
        "create_unix_server",
        "create_datagram_endpoint",
        "connect_accepted_socket",
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


@dataclass
class _ModuleAliases:
    """Local names bound to ``os`` / ``asyncio`` (import-as and simple assigns)."""

    os_names: set[str] = field(default_factory=lambda: {"os"})
    asyncio_names: set[str] = field(default_factory=lambda: {"asyncio"})

    def is_os(self, name: str) -> bool:
        return name in self.os_names

    def is_asyncio(self, name: str) -> bool:
        return name in self.asyncio_names


def _collect_module_aliases(tree: ast.AST) -> _ModuleAliases:
    """Map ``import os as o`` / ``x = os`` so owner-bound bans still apply.

    Owner checks for ``os.*`` / ``asyncio.*`` used to require the literal name
    ``os`` / ``asyncio``, so ``import os as o; o.system(...)`` and
    ``getattr(o, "system")`` bypassed the Attribute / getattr gates.
    """
    aliases = _ModuleAliases()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Exact module only — ``import os.path as osp`` is not ``os``.
                if alias.name == "os":
                    aliases.os_names.add(alias.asname or "os")
                elif alias.name == "asyncio":
                    aliases.asyncio_names.add(alias.asname or "asyncio")
        elif isinstance(node, ast.ImportFrom) and node.module is None:
            for alias in node.names:
                if alias.name == "os":
                    aliases.os_names.add(alias.asname or "os")
                elif alias.name == "asyncio":
                    aliases.asyncio_names.add(alias.asname or "asyncio")

    # Fixpoint: ``x = os`` / ``y = x`` after import-as (walk order ≠ exec order).
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            src_name: str | None = None
            targets: list[ast.Name] = []
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                src_name = node.value.id
                targets = [t for t in node.targets if isinstance(t, ast.Name)]
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Name)
            ):
                src_name = node.value.id
                targets = [node.target]
            if src_name is None or not targets:
                continue
            if aliases.is_os(src_name):
                for t in targets:
                    if t.id not in aliases.os_names:
                        aliases.os_names.add(t.id)
                        changed = True
            elif aliases.is_asyncio(src_name):
                for t in targets:
                    if t.id not in aliases.asyncio_names:
                        aliases.asyncio_names.add(t.id)
                        changed = True
    return aliases


def assert_safe_blueprint_source(source: str) -> None:
    """Raise ``ValueError`` if *source* uses banned constructs.

    This is a static AST check — not a full sandbox.  It blocks common
    escape hatches stronger than a plain substring ban list.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Blueprint source has invalid syntax: {exc}") from exc

    aliases = _collect_module_aliases(tree)
    for node in ast.walk(tree):
        _check_node(node, aliases)


def _check_node(node: ast.AST, aliases: _ModuleAliases) -> None:
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
            # ``from asyncio import create_subprocess_exec`` / open_connection
            if node.module == "asyncio":
                for alias in node.names:
                    if (
                        alias.name in _BANNED_ASYNCIO_ATTRS
                        or alias.name in BANNED_CALL_NAMES
                    ):
                        raise ValueError(
                            f"Banned import of asyncio.{alias.name} in user "
                            f"blueprint (line {getattr(node, 'lineno', '?')})"
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
        _check_call(node, aliases)
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


def _check_call(node: ast.Call, aliases: _ModuleAliases) -> None:
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

    # getattr(os, "system") / getattr(asyncio, "create_subprocess_exec") bypass
    # Attribute-node bans when the attr name is a string constant — reject those.
    if name == "getattr":
        _check_getattr_escape(node, aliases)

    # os.* / asyncio.* owner checks before builtin open() so ``os.open`` is
    # banned outright and does not fall through to read-mode open() logic.
    # Alias-aware: ``import os as o; o.system`` must not bypass ``os.system``.
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        owner = node.func.value.id
        attr = node.func.attr
        if aliases.is_os(owner) and attr in _BANNED_OS_ATTRS:
            raise ValueError(
                f"Banned call to os.{attr} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )
        if aliases.is_asyncio(owner) and attr in _BANNED_ASYNCIO_ATTRS:
            raise ValueError(
                f"Banned call to asyncio.{attr} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )

    if name == "open":
        _check_open_call(node)
        return

    if isinstance(node.func, ast.Attribute):
        attr = node.func.attr

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


def _check_getattr_escape(node: ast.Call, aliases: _ModuleAliases) -> None:
    """Reject ``getattr(os, "system")`` / ``getattr(asyncio, "…")`` constant escapes.

    Direct ``os.system`` is already banned via Attribute checks; reflection with
    a literal attribute name must not reopen those APIs. Dynamic attribute names
    (variables / expressions) are left to runtime policy, matching open(mode=).
    Also covers ``import os as o; getattr(o, "system")``.
    """
    if len(node.args) < 2:
        return
    owner_node, attr_node = node.args[0], node.args[1]
    if not isinstance(owner_node, ast.Name):
        return
    if not isinstance(attr_node, ast.Constant) or not isinstance(attr_node.value, str):
        return
    owner = owner_node.id
    attr = attr_node.value
    if aliases.is_os(owner) and attr in _BANNED_OS_ATTRS:
        raise ValueError(
            f"Banned getattr(os, {attr!r}) in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )
    if aliases.is_asyncio(owner) and (
        attr in _BANNED_ASYNCIO_ATTRS or attr in BANNED_CALL_NAMES
    ):
        raise ValueError(
            f"Banned getattr(asyncio, {attr!r}) in user blueprint "
            f"(line {getattr(node, 'lineno', '?')})"
        )


def _looks_like_open_mode(value: str) -> bool:
    """True for short open()/Path.open mode strings (r/w/a/x + optional b/t/+).

    Used so ``Path(...).open('w')`` (mode is 1st positional) is not confused
    with ``io.open('/path/with/w', 'r')`` (path is 1st positional).
    """
    if not value or len(value) > 4:
        return False
    return all(c in "rwaxtbU+" for c in value) and any(c in "rwax" for c in value)


def _is_write_open_mode(mode: str) -> bool:
    return mode in _WRITE_OPEN_MODES or any(c in mode for c in ("w", "a", "x"))


def _check_open_call(node: ast.Call) -> None:
    """Reject ``open(..., 'w')`` / ``Path.open('w')`` / keyword mode= write variants.

    Builtin ``open(file, mode)`` and ``io.open`` / ``codecs.open`` put mode in
    the 2nd positional arg. ``pathlib.Path.open(mode)`` puts mode first — the
    prior check only looked at args[1]/kwargs, so ``Path('/tmp/x').open('w')``
    bypassed the write ban (while ``Path(...).open(mode='w')`` was caught).
    """
    modes: list[str] = []
    # Builtin / io.open / codecs.open: open(file, mode)
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(
        node.args[1].value, str
    ):
        modes.append(node.args[1].value)
    # pathlib.Path.open(mode[, ...]): mode is first positional after receiver
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and _looks_like_open_mode(node.args[0].value)
    ):
        modes.append(node.args[0].value)
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(
            kw.value.value, str
        ):
            modes.append(kw.value.value)
    if not modes:
        # open(path) defaults to read; dynamic mode left to runtime policy
        return
    for mode in modes:
        if _is_write_open_mode(mode):
            raise ValueError(
                f"Banned open() with write mode {mode!r} in user blueprint "
                f"(line {getattr(node, 'lineno', '?')})"
            )
