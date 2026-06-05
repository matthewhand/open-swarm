from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    """Abstract interface for agent memory."""

    @abstractmethod
    def add(self, data: str, metadata: dict[str, Any] = None) -> None:
        """Add data to memory."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for relevant context."""
        pass
