"""Generic, injectable filesystem toolset for blueprints.

A small, safety-first abstraction so blueprints (cli_* wrappers AND native
Python blueprints) can be granted filesystem access *declaratively* instead of
each one re-implementing ``open()`` with no guard rails.

Design goals
------------
- **Permission levels**: ``none`` | ``readonly`` | ``readwrite`` (writes require
  an explicit opt-in, never the default).
- **Path allow-listing**: every operation is resolved to a real path and must sit
  inside one of the configured ``allowed_paths`` roots (symlink-escape proof).
- **Size limits**: reads and writes are capped (``max_read_bytes`` /
  ``max_write_bytes``); directory listings are capped (``max_list_entries``).
- **Audit logging**: every op is logged to ``swarm.filesystem.audit``.

Integration
-----------
- ``FilesystemToolset.from_config(config)`` builds an instance from the
  ``filesystem`` block of ``swarm_config.json`` (with optional per-request
  overrides), so toolsets are declared in config.
- ``toolset.as_function_tools()`` returns ``openai-agents`` ``function_tool``
  objects ready to drop into a native blueprint's ``Agent(tools=[...])``.
- The plain methods (``read``/``list``/``stat``/``tree``/``write``) are also
  usable directly (e.g. by the ``fs_introspect`` blueprint for instant,
  LLM-free introspection over the OpenAI-compatible API).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("swarm.filesystem.audit")

# Permission levels
NONE = "none"
READONLY = "readonly"
READWRITE = "readwrite"
_LEVELS = (NONE, READONLY, READWRITE)


class FilesystemError(Exception):
    """Base error for filesystem-toolset operations (safe to surface to callers)."""


class PermissionDenied(FilesystemError):
    """The toolset's permission level forbids this operation."""


class PathNotAllowed(FilesystemError):
    """The target path is outside the configured allow-list."""


def _is_within(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass
class FilesystemToolset:
    """A scoped, auditable filesystem accessor."""

    permission: str = READONLY
    allowed_paths: list[str] = field(default_factory=list)
    max_read_bytes: int = 1_000_000          # 1 MB
    max_write_bytes: int = 1_000_000
    max_list_entries: int = 2000
    audit: bool = True

    # Reasonable default roots when config supplies none (read-only introspection).
    DEFAULT_ROOTS: ClassVar[tuple[str, ...]] = (
        "~/.config/swarm",
        "~/open-swarm",
        "~/.local/share/swarm",
    )

    def __post_init__(self) -> None:
        if self.permission not in _LEVELS:
            raise ValueError(f"permission must be one of {_LEVELS}, got {self.permission!r}")
        roots = self.allowed_paths or list(self.DEFAULT_ROOTS)
        self._roots: list[Path] = []
        for p in roots:
            try:
                self._roots.append(Path(p).expanduser().resolve())
            except Exception:  # pragma: no cover - defensive
                logger.warning("filesystem toolset: skipping unresolvable root %r", p)

    # ---- internals -------------------------------------------------------
    def _resolve(self, path: str | os.PathLike) -> Path:
        """Resolve *path* (following symlinks) and enforce the allow-list."""
        rp = Path(path).expanduser().resolve()
        if not any(_is_within(rp, root) or rp == root for root in self._roots):
            self._audit("resolve", str(rp), False, "outside allow-list")
            raise PathNotAllowed(
                f"{rp} is outside the allowed roots: {[str(r) for r in self._roots]}"
            )
        return rp

    def _audit(self, op: str, path: str, ok: bool, detail: str = "") -> None:
        if self.audit:
            audit_logger.info("op=%s ok=%s path=%s %s", op, ok, path, detail)

    def _require(self, *levels: str) -> None:
        if self.permission not in levels:
            raise PermissionDenied(
                f"operation requires permission in {levels}, toolset is '{self.permission}'"
            )

    # ---- read-side operations -------------------------------------------
    def read(self, path: str) -> str:
        self._require(READONLY, READWRITE)
        rp = self._resolve(path)
        if not rp.is_file():
            raise FilesystemError(f"not a file: {rp}")
        size = rp.stat().st_size
        data = rp.read_text(encoding="utf-8", errors="replace")
        truncated = len(data.encode("utf-8", "replace")) > self.max_read_bytes
        if truncated:
            data = data[: self.max_read_bytes]
        self._audit("read", str(rp), True, f"{size}b truncated={truncated}")
        return data + ("\n…[truncated]" if truncated else "")

    def list(self, path: str) -> list[dict[str, Any]]:
        self._require(READONLY, READWRITE)
        rp = self._resolve(path)
        if not rp.is_dir():
            raise FilesystemError(f"not a directory: {rp}")
        out: list[dict[str, Any]] = []
        for i, entry in enumerate(sorted(rp.iterdir(), key=lambda e: e.name)):
            if i >= self.max_list_entries:
                out.append({"name": "…[truncated]", "type": "note"})
                break
            try:
                st = entry.stat()
                out.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": st.st_size,
                })
            except OSError:
                out.append({"name": entry.name, "type": "unreadable"})
        self._audit("list", str(rp), True, f"{len(out)} entries")
        return out

    def stat(self, path: str) -> dict[str, Any]:
        self._require(READONLY, READWRITE)
        rp = self._resolve(path)
        st = rp.stat()
        info = {
            "path": str(rp),
            "type": "dir" if rp.is_dir() else "file" if rp.is_file() else "other",
            "size": st.st_size,
            "mode": oct(st.st_mode & 0o777),
            "mtime": int(st.st_mtime),
        }
        self._audit("stat", str(rp), True)
        return info

    def tree(self, path: str, max_depth: int = 2) -> str:
        self._require(READONLY, READWRITE)
        root = self._resolve(path)
        if not root.is_dir():
            raise FilesystemError(f"not a directory: {root}")
        lines: list[str] = [str(root)]
        count = 0

        def walk(d: Path, prefix: str, depth: int) -> None:
            nonlocal count
            if depth > max_depth or count >= self.max_list_entries:
                return
            try:
                entries = sorted(d.iterdir(), key=lambda e: (e.is_file(), e.name))
            except OSError:
                return
            for e in entries:
                if count >= self.max_list_entries:
                    lines.append(prefix + "…[truncated]")
                    return
                count += 1
                lines.append(f"{prefix}{'📁' if e.is_dir() else '📄'} {e.name}")
                if e.is_dir():
                    walk(e, prefix + "  ", depth + 1)

        walk(root, "  ", 1)
        self._audit("tree", str(root), True, f"{count} nodes")
        return "\n".join(lines)

    # ---- write-side operations (opt-in only) ----------------------------
    def write(self, path: str, content: str) -> dict[str, Any]:
        self._require(READWRITE)
        if len(content.encode("utf-8", "replace")) > self.max_write_bytes:
            raise FilesystemError(
                f"content exceeds max_write_bytes ({self.max_write_bytes})"
            )
        rp = self._resolve(path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(content, encoding="utf-8")
        self._audit("write", str(rp), True, f"{len(content)}c")
        return {"path": str(rp), "bytes": len(content.encode("utf-8", "replace"))}

    # ---- construction & integration -------------------------------------
    @classmethod
    def from_config(
        cls,
        config: dict[str, Any] | None,
        *,
        section: str = "filesystem",
        overrides: dict[str, Any] | None = None,
    ) -> "FilesystemToolset":
        """Build a toolset from the ``filesystem`` block of swarm_config.

        Recognised keys: ``permission``, ``allowed_paths``, ``max_read_bytes``,
        ``max_write_bytes``, ``max_list_entries``, ``audit``. ``overrides`` (e.g.
        per-request params) take precedence but can NEVER escalate ``readwrite``
        unless the config already granted it.
        """
        block = dict(((config or {}).get(section)) or {})
        block.update({k: v for k, v in (overrides or {}).items() if v is not None})
        cfg_perm = (((config or {}).get(section)) or {}).get("permission", READONLY)
        req_perm = block.get("permission", cfg_perm)
        # never let a request escalate beyond what config allows
        if cfg_perm != READWRITE and req_perm == READWRITE:
            req_perm = cfg_perm
        return cls(
            permission=req_perm or READONLY,
            allowed_paths=block.get("allowed_paths") or [],
            max_read_bytes=int(block.get("max_read_bytes", 1_000_000)),
            max_write_bytes=int(block.get("max_write_bytes", 1_000_000)),
            max_list_entries=int(block.get("max_list_entries", 2000)),
            audit=bool(block.get("audit", True)),
        )

    def as_function_tools(self) -> list[Any]:
        """Wrap the read (and, if permitted, write) ops as ``function_tool``s.

        Returns an empty list if the ``agents`` SDK is unavailable, so importing
        this module never hard-fails in CLI-only deployments.
        """
        try:
            from agents import function_tool
        except Exception:  # pragma: no cover - SDK optional
            logger.debug("agents SDK not available; as_function_tools() -> []")
            return []

        def fs_read_file(path: str) -> str:
            """Read a UTF-8 text file (size-capped, allow-list enforced)."""
            return self.read(path)

        def fs_list_dir(path: str) -> str:
            """List a directory's entries (name, type, size)."""
            return "\n".join(f"{e['type']:5} {e.get('size','-'):>10} {e['name']}" for e in self.list(path))

        def fs_stat(path: str) -> str:
            """Stat a path (type, size, mode, mtime)."""
            return str(self.stat(path))

        tools = [function_tool(fs_read_file), function_tool(fs_list_dir), function_tool(fs_stat)]
        if self.permission == READWRITE:
            def fs_write_file(path: str, content: str) -> str:
                """Write UTF-8 text to a file (size-capped, allow-list enforced)."""
                return str(self.write(path, content))
            tools.append(function_tool(fs_write_file))
        return tools
