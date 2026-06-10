"""Placeholder for a future `langmem` memory backend.

This backend is NOT implemented yet. ``get_memory_backend`` logs a warning
and returns ``None`` when ``"backend": "langmem"`` is configured, so
blueprints degrade gracefully. Constructing :class:`LangmemMemory` directly
raises :class:`NotImplementedError`.
"""

import logging
from typing import Any

from swarm.memory.base import BaseMemory

logger = logging.getLogger(__name__)


class LangmemMemory(BaseMemory):
    """Stub for the langmem memory backend (not yet implemented)."""

    def __init__(self, config: dict[str, Any] | None = None):
        raise NotImplementedError(
            "The 'langmem' memory backend is a placeholder and is not implemented yet. "
            "Use 'mem0' (install with `pip install open-swarm[memory]`) instead."
        )

    def add(self, messages: Any, user_id: str = "default", metadata: dict[str, Any] | None = None) -> None:
        raise NotImplementedError("langmem backend is not implemented yet.")

    def search(self, query: str, user_id: str = "default", limit: int | None = None) -> list[str]:
        raise NotImplementedError("langmem backend is not implemented yet.")
