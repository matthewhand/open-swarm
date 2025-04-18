import os
from dotenv import load_dotenv; load_dotenv(override=True)

import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional
import argparse

# Set logging to WARNING by default unless SWARM_DEBUG=1
if not os.environ.get("SWARM_DEBUG"):
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.DEBUG)

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from typing import Optional
from pathlib import Path
try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in ChatbotBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Define the Blueprint ---
class ChatbotBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[Path] = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

        # Remove redundant client instantiation; rely on framework-level default client
        # (No need to re-instantiate AsyncOpenAI or set_default_openai_client)
        # All blueprints now use the default client set at framework init

    """A simple conversational chatbot agent."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "ChatbotBlueprint",
        "title": "Simple Chatbot",
        "description": "A basic conversational agent that responds to user input.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["chatbot", "conversation", "simple"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance, respecting LITELLM_MODEL/DEFAULT_LLM if set."""
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        # Patch: Respect LITELLM_MODEL/DEFAULT_LLM env vars
        import os
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or profile_data.get("model")
        profile_data["model"] = model_name
        if profile_data.get("provider", "openai").lower() != "openai": raise ValueError(f"Unsupported provider: {profile_data.get('provider')}")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")

        # REMOVE PATCH: env expansion is now handled globally in config loader
        client_cache_key = f"{profile_data.get('provider', 'openai')}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM: {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the single Chatbot agent."""
        logger.debug("Creating Chatbot agent...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Chatbot.")
        model_instance = self._get_model_instance(default_profile_name)

        chatbot_instructions = "You are a helpful and friendly chatbot. Respond directly to the user's input in a conversational manner."

        chatbot_agent = Agent(
            name="Chatbot",
            model=model_instance,
            instructions=chatbot_instructions,
            tools=[], # No function tools needed for simple chat
            mcp_servers=mcp_servers # Pass along, though likely unused
        )

        logger.debug("Chatbot agent created.")
        return chatbot_agent

    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        """Main execution entry point for the Chatbot blueprint."""
        logger.info("ChatbotBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        async for chunk in self._run_non_interactive(instruction, **kwargs):
            yield chunk
        logger.info("ChatbotBlueprint run method finished.")

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        from agents import Runner
        import os
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
        try:
            result = await Runner.run(agent, instruction)
            yield {"messages": [{"role": "assistant", "content": getattr(result, 'final_output', str(result))}]}
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

# Standard Python entry point
if __name__ == "__main__":
    import sys
    import asyncio
    # --- AUTO-PYTHONPATH PATCH FOR AGENTS ---
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    parser = argparse.ArgumentParser(description='Chatbot Blueprint Runner')
    parser.add_argument('instruction', nargs=argparse.REMAINDER, help='Instruction for Chatbot to process (all args after -- are joined as the prompt)')
    args = parser.parse_args()
    instruction_args = args.instruction
    if instruction_args and instruction_args[0] == '--':
        instruction_args = instruction_args[1:]
    instruction = ' '.join(instruction_args).strip() if instruction_args else None
    if instruction:
        blueprint = ChatbotBlueprint(blueprint_id="chatbot")
        async def runner():
            async for chunk in blueprint._run_non_interactive(instruction):
                msg = chunk["messages"][0]["content"]
                if not msg.startswith("An error occurred:"):
                    print(msg)
        asyncio.run(runner())
    else:
        print("Interactive mode not supported in this script.")
