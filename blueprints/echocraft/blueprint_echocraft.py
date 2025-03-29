import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in EchoCraftBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Define the Blueprint ---
class EchoCraftBlueprint(BlueprintBase):
    """A simple blueprint that echoes the user's instruction."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "EchoCraftBlueprint",
        "title": "EchoCraft",
        "description": "A simple agent that echoes the provided instruction.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["simple", "echo", "testing"],
        "required_mcp_servers": [], # No MCP needed
        "env_vars": [], # No specific env vars needed
    }

    # Caches (Standard practice, though not strictly needed for this simple BP)
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        if provider != "openai": # Keep simple for now
            logger.error(f"Unsupported LLM provider '{provider}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init OpenAI client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM provider: {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the EchoAgent."""
        logger.debug("Creating EchoAgent...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        # Get model instance (even though EchoAgent won't use it for LLM calls, Agent requires it)
        default_profile_name = self.config.get("llm_profile", "default")
        model_instance = self._get_model_instance(default_profile_name)

        # Define the EchoAgent. It doesn't need tools or complex instructions.
        # It overrides the process method to simply return the input.
        class EchoAgent(Agent):
            async def process(self, input_data: Any, **kwargs) -> Any:
                """Overrides the default process method to simply echo the input."""
                logger.info(f"EchoAgent received input: {input_data}")
                # We need to return something the Runner expects as output.
                # The simplest is just returning the input string.
                return str(input_data) if input_data is not None else "[No input received]"

        echo_agent = EchoAgent(
            name="Echo",
            model=model_instance, # Still required by Agent base class
            instructions="You are a simple echo agent. You don't need to process instructions.", # Basic instructions
            tools=[], # No tools needed
            mcp_servers=mcp_servers # Pass along, though unused
        )

        logger.debug("EchoAgent created.")
        return echo_agent

# Standard Python entry point
if __name__ == "__main__":
    EchoCraftBlueprint.main()
