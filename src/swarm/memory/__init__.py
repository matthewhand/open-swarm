"""Optional, opt-in memory backends for Swarm blueprints.

A blueprint enables memory via its config block, e.g.:

    {
        "blueprints": {
            "my_blueprint": {
                "memory": {"backend": "mem0", "user_id": "alice", "limit": 5}
            }
        }
    }

or a top-level ``"memory": {"backend": "mem0", ...}`` block. When no such
block is present (or the backend's package is not installed),
:func:`get_memory_backend` returns ``None`` and blueprints behave exactly as
before — memory is strictly opt-in.
"""

import logging
from typing import Any, Protocol, runtime_checkable

from .base import BaseMemory

logger = logging.getLogger(__name__)

__all__ = ["BaseMemory", "MemoryBackend", "get_memory_backend"]


@runtime_checkable
class MemoryBackend(Protocol):
    """Minimal interface a memory backend must provide.

    Any object with these two methods (e.g. :class:`~swarm.memory.mem0_memory.Mem0Memory`
    or an in-memory fake in tests) can be used as a blueprint memory backend.
    """

    def search(self, query: str, user_id: str = "default") -> list[str]:
        """Return memory snippets relevant to ``query`` for ``user_id``."""
        ...

    def add(self, messages: list[dict[str, Any]], user_id: str = "default") -> None:
        """Persist a conversation (list of ``{"role": ..., "content": ...}`` dicts)."""
        ...


def get_memory_backend(config: Any = None, options: dict | None = None) -> "MemoryBackend | None":
    """Factory for memory backends. Returns ``None`` unless memory is enabled.

    Accepts either the new style — a config dict like
    ``{"backend": "mem0", ...}`` — or the legacy style of a backend name
    string plus an options dict (``get_memory_backend("mem0", {...})``).

    The backend package (e.g. ``mem0``) is imported lazily; if it is not
    installed, a warning is logged and ``None`` is returned so blueprints
    degrade gracefully when the ``[memory]`` extra is absent.
    """
    if isinstance(config, str):
        merged = dict(options or {})
        merged["backend"] = config
        config = merged
    if not isinstance(config, dict):
        return None

    backend = str(config.get("backend") or "").lower().strip()
    if not backend or backend == "none":
        return None

    if backend == "mem0":
        try:
            from .mem0_memory import Mem0Memory
            return Mem0Memory(config)
        except ImportError as e:
            logger.warning(
                "Memory backend 'mem0' requested but the 'mem0ai' package is not "
                "installed (install with `pip install open-swarm[memory]`). "
                "Continuing without memory. (%s)", e,
            )
            return None

    if backend in ("langmem", "papr"):
        logger.warning(
            "Memory backend '%s' is a placeholder and not yet implemented. "
            "Continuing without memory.", backend,
        )
        return None

    logger.warning("Unknown memory backend '%s'. Continuing without memory.", backend)
    return None
