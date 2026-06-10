from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    """Abstract base class for agent memory backends.

    Concrete backends must implement :meth:`add` and :meth:`search` and
    thereby satisfy the :class:`swarm.memory.MemoryBackend` protocol.
    """

    @abstractmethod
    def add(self, messages: Any, user_id: str = "default", metadata: dict[str, Any] | None = None) -> None:
        """Persist a conversation (list of role/content dicts) or a plain string."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, user_id: str = "default", limit: int | None = None) -> list[str]:
        """Return memory snippets relevant to ``query`` for ``user_id``."""
        raise NotImplementedError
