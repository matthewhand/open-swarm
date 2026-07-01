"""fs_introspect — instant, LLM-free filesystem introspection over the API.

Why this exists
---------------
Asking ``cli_agent`` to "read swarm_config.json" shells out to an agentic CLI
that runs a multi-turn LLM loop (~130–200s here) and often can't read files in
non-interactive mode — so connector clients (Grok) time out. ``fs_introspect``
answers the same questions **synchronously and deterministically**: it resolves
a path through the safety-checked :class:`~swarm.core.filesystem_toolset.FilesystemToolset`
and returns the bytes/listing directly. No model call, sub-second latency.

Usage (OpenAI-compatible)
-------------------------
    {"model": "fs_introspect",
     "messages": [{"role": "user", "content": "read ~/.config/swarm/swarm_config.json"}]}

Grammar (first word of the message, else inferred):
    read|cat <path>     -> file contents
    list|ls   <path>    -> directory listing
    stat      <path>    -> path metadata
    tree      <path>    -> shallow tree
A bare path reads it (or lists it, if it's a directory).

Structured params also work: ``params: {"op": "read", "path": "..."}``.
Permission level and allow-listed roots come from the ``filesystem`` block of
swarm_config.json (default: readonly, scoped to the swarm config/app/data dirs).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.filesystem_toolset import FilesystemError, FilesystemToolset

logger = logging.getLogger(__name__)

_OPS = {"read", "cat", "list", "ls", "stat", "tree", "grep", "find", "head", "tail"}


class FsIntrospectBlueprint(BlueprintBase):
    """Fast, read-only filesystem introspection (no LLM)."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "fs_introspect",
        "title": "Filesystem Introspect (instant, no LLM)",
        "description": (
            "Read files / list dirs / stat paths directly via the safety-checked "
            "filesystem toolset. Sub-second, deterministic — built for reliable "
            "config/log/code inspection by connector clients without CLI timeouts."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["filesystem", "introspection", "tools", "readonly"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "fs_introspect", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    @staticmethod
    def _last_user_text(messages: list[dict[str, Any]]) -> str:
        for m in reversed(messages or []):
            if (m.get("role") or "user") == "user" and m.get("content"):
                return str(m["content"]).strip()
        return support.render_prompt(messages).strip()

    def _parse(self, messages: list[dict[str, Any]]) -> tuple[str, str]:
        """Return (op, path) from params or the message grammar."""
        params = dict(self._params)
        if params.get("path"):
            return (str(params.get("op") or "read").lower(), str(params["path"]))
        text = self._last_user_text(messages)
        if not text:
            return ("", "")
        first, _, rest = text.partition(" ")
        if first.lower() in _OPS and rest.strip():
            return (first.lower(), rest.strip())
        # bare path (or natural-language fallback: grab the last token that looks pathish)
        token = text
        if " " in text:
            cand = [t for t in text.split() if ("/" in t or t.startswith("~") or "." in t)]
            if not cand:
                return ("", "")
            token = cand[-1]
        return ("auto", token.strip())

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        op, path = self._parse(messages)
        if not path:
            yield support.message_chunk(
                "Usage: `read|list|stat|tree <path>` (e.g. `read ~/.config/swarm/swarm_config.json`).",
                final=True,
                meta=support.backend_meta(["fs_introspect"]),
            )
            return

        fs = FilesystemToolset.from_config(self._config, overrides=self._params)
        try:
            if op == "grep":
                # grammar: grep <pattern> <path>   (params: pattern, path)
                pattern = self._params.get("pattern")
                target = path
                if not pattern:
                    pattern, _, rest = path.partition(" ")
                    target = rest.strip() or "."
                out = fs.grep(pattern, target)
            elif op == "find":
                # grammar: find <glob> [in <dir>]   (params: glob, path)
                glob = self._params.get("glob")
                root = self._params.get("path")
                if not glob:
                    parts = path.split()
                    glob = parts[0]
                    root = parts[2] if len(parts) >= 3 and parts[1] == "in" else (parts[1] if len(parts) >= 2 else None)
                out = fs.find(glob, root)
            elif op in ("head", "tail"):
                # grammar: head|tail <path> [n]   (params: path, n)
                n = self._params.get("n")
                target = path
                if n is None and len(path.split()) >= 2:
                    bits = path.split()
                    target = bits[0]
                    n = int(bits[1]) if bits[1].isdigit() else None
                n = int(n) if n is not None else 50
                out = fs.head(target, n) if op == "head" else fs.tail(target, n)
            elif op in ("read", "cat"):
                sl = self._params.get("start_line")
                el = self._params.get("end_line")
                # grammar: read <path> <start> <end>
                if sl is None and el is None and len(path.split()) >= 2:
                    bits = path.split()
                    path = bits[0]
                    sl = int(bits[1]) if len(bits) >= 2 and bits[1].isdigit() else None
                    el = int(bits[2]) if len(bits) >= 3 and bits[2].isdigit() else None
                out = fs.read(path, start_line=sl, end_line=el)
            elif op in ("list", "ls"):
                out = "\n".join(
                    f"{e['type']:5} {str(e.get('size','-')):>10}  {e['name']}" for e in fs.list(path)
                )
            elif op == "stat":
                out = "\n".join(f"{k}: {v}" for k, v in fs.stat(path).items())
            elif op == "tree":
                out = fs.tree(path)
            else:  # auto: list dirs, read files
                from pathlib import Path as _P
                rp = _P(path).expanduser()
                if rp.is_dir():
                    out = "\n".join(
                        f"{e['type']:5} {str(e.get('size','-')):>10}  {e['name']}" for e in fs.list(path)
                    )
                else:
                    out = fs.read(path)
        except FilesystemError as e:
            yield support.message_chunk(
                f"filesystem error: {e}", final=True, meta=support.backend_meta(["fs_introspect"])
            )
            return

        yield support.message_chunk(out, final=True, meta=support.backend_meta(["fs_introspect"]))
