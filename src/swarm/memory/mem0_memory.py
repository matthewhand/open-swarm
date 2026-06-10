import logging
from typing import Any

from swarm.memory.base import BaseMemory

logger = logging.getLogger(__name__)


class Mem0Memory(BaseMemory):
    """Memory backend backed by the `mem0` package (`pip install open-swarm[memory]`).

    Raises ImportError at construction time when `mem0` is not installed;
    :func:`swarm.memory.get_memory_backend` catches this and degrades to no memory.

    Config keys (all optional besides ``backend``):
      - ``config``: dict passed to ``mem0.Memory.from_config`` (vector store, llm, ...)
      - ``limit``: max results returned by :meth:`search` (default 5)
      - ``user_id``: default user id used by blueprints when none is supplied
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = dict(config or {})
        # Lazy import: only required when the mem0 backend is actually enabled.
        from mem0 import Memory  # raises ImportError when the extra is missing
        mem0_config = self.config.get("config")
        if mem0_config:
            self.memory = Memory.from_config(mem0_config)
        else:
            self.memory = Memory()

    def add(self, messages: Any, user_id: str = "default", metadata: dict[str, Any] | None = None) -> None:
        """Persist a conversation (list of role/content dicts) or a plain string."""
        # Back-compat: callers that pass metadata={"user_id": ...} (old signature).
        if metadata and metadata.get("user_id") and user_id == "default":
            user_id = metadata["user_id"]
        self.memory.add(messages, user_id=user_id, metadata=metadata)

    def search(self, query: str, user_id: str = "default", limit: int | None = None) -> list[str]:
        """Return memory snippets relevant to ``query`` for ``user_id``."""
        limit = limit or self.config.get("limit", 5)
        results = self.memory.search(query=query, user_id=user_id, limit=limit)
        # mem0 may return either a list of hits or {"results": [...]}.
        if isinstance(results, dict):
            results = results.get("results", [])
        snippets: list[str] = []
        for res in results or []:
            if isinstance(res, dict):
                snippets.append(str(res.get("memory", res)))
            else:
                snippets.append(str(res))
        return snippets
