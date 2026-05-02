from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseMemory(ABC):
    """Abstract interface for agent memory."""
    
    @abstractmethod
    def add(self, data: str, metadata: Dict[str, Any] = None) -> None:
        """Add data to memory."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant context."""
        pass
