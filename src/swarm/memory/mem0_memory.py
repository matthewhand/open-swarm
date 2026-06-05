import logging
from typing import Any

from swarm.memory.base import BaseMemory

logger = logging.getLogger(__name__)

class Mem0Memory(BaseMemory):
    """Integration for mem0 memory backend."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        try:
            from mem0 import Memory
            self.memory = Memory.from_config(self.config)
        except ImportError:
            logger.warning("mem0 package not installed. Mem0Memory will not function correctly.")
            self.memory = None

    def add(self, data: str, metadata: dict[str, Any] = None) -> None:
        if self.memory:
            user_id = (metadata or {}).get("user_id", "default_user")
            self.memory.add(data, user_id=user_id, metadata=metadata)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.memory:
            return []

        # mem0 generally returns related documents or strings based on search
        results = self.memory.search(query=query, limit=limit)

        # Format the results into conversational context
        formatted_context = [{"role": "system", "content": f"Prior context: {res['memory']}"} for res in results]
        return formatted_context
