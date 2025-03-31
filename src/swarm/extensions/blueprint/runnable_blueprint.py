import abc
from typing import List, Dict, Any, AsyncGenerator

# Assuming blueprint_base is in the same directory or accessible via installed package
from .blueprint_base import BlueprintBase

class RunnableBlueprint(BlueprintBase, abc.ABC):
    """
    Abstract base class for blueprints designed to be executed programmatically,
    typically via an API endpoint like swarm-api.

    Inherits common functionality from BlueprintBase and requires subclasses
    to implement the `run` method as the standard entry point for execution.
    """

    @abc.abstractmethod
    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Abstract method defining the standard entry point for running the blueprint
        programmatically.

        Args:
            messages: A list of message dictionaries, typically following the
                      OpenAI chat completions format. The last message is usually
                      the user's input or instruction.
            **kwargs: Additional keyword arguments that might be passed by the
                      runner (e.g., mcp_servers, configuration overrides).

        Yields:
            Dictionaries representing chunks of the response, often containing
            a 'messages' key with a list of message objects. The exact format
            may depend on the runner's expectations (e.g., SSE for streaming).

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses of RunnableBlueprint must implement the 'run' method.")
        # This yield is technically unreachable but satisfies static analysis
        # expecting a generator function body.
        if False:
             yield {}

