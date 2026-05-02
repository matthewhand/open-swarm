from .base import BaseMemory
from .mem0_memory import Mem0Memory
from .langmem_memory import LangmemMemory
from .papr_memory import PaprMemory

def get_memory_backend(backend_name: str, config: dict = None) -> BaseMemory:
    """Factory method to instantiate the correct memory backend."""
    config = config or {}
    name = backend_name.lower().strip()
    
    if name == 'mem0':
        return Mem0Memory(config)
    elif name == 'langmem':
        return LangmemMemory(config)
    elif name == 'papr':
        return PaprMemory(config)
    
    return None
