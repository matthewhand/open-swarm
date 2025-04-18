import logging
import os
import sys
from typing import Dict, Any, List, TypedDict, ClassVar, Optional
from datetime import datetime
import pytz
from pathlib import Path

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
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
     print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     sys.exit(1)

logger = logging.getLogger(__name__)

# --- Define the desired output structure ---
class SuggestionsOutput(TypedDict):
    """Defines the expected structure for the agent's output."""
    suggestions: List[str]

# --- Define the Blueprint ---
# === OpenAI GPT-4.1 Prompt Engineering Guide ===
# See: https://github.com/openai/openai-cookbook/blob/main/examples/gpt4-1_prompting_guide.ipynb
#
# Agentic System Prompt Example (recommended for structured output/suggestion agents):
SYS_PROMPT_AGENTIC = """
You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.
"""

class SuggestionBlueprint(BlueprintBase):
    """A blueprint defining an agent that generates structured JSON suggestions using output_type."""

    metadata: ClassVar[Dict[str, Any]] = {
        "name": "SuggestionBlueprint",
        "title": "Suggestion Blueprint (Structured Output)",
        "description": "An agent that provides structured suggestions using Agent(output_type=...).",
        "version": "1.2.0", # Version bump for refactor
        "author": "Open Swarm Team (Refactored)",
        "tags": ["structured output", "json", "suggestions", "output_type"],
        "required_mcp_servers": [],
        "env_vars": [], # OPENAI_API_KEY is implicitly needed by the model
    }

    # Caches
    _model_instance_cache: Dict[str, Model] = {}

    def __init__(self, blueprint_id: str = None, config_path: Optional[Path] = None, **kwargs):
        if blueprint_id is None:
            blueprint_id = "suggestion"
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data: raise ValueError(f"Missing LLM profile '{profile_name}'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")
        if provider != "openai": raise ValueError(f"Unsupported provider: {provider}")
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM: {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Create the SuggestionAgent."""
        logger.debug("Creating SuggestionAgent...")
        self._model_instance_cache = {}
        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for SuggestionAgent.")
        model_instance = self._get_model_instance(default_profile_name)
        suggestion_agent_instructions = (
            "You are the SuggestionAgent. Analyze the user's input and generate exactly three relevant, "
            "concise follow-up questions or conversation starters as a JSON object with a single key 'suggestions' "
            "containing a list of strings."
        )
        suggestion_agent = Agent(
            name="SuggestionAgent",
            instructions=suggestion_agent_instructions,
            tools=[],
            model=model_instance,
            output_type=SuggestionsOutput,
            mcp_servers=mcp_servers
        )
        logger.debug("SuggestionAgent created with output_type enforcement.")
        return suggestion_agent

    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        """Main execution entry point for the Suggestion blueprint."""
        logger.info("SuggestionBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        async for chunk in self._run_non_interactive(instruction, **kwargs):
            yield chunk
        logger.info("SuggestionBlueprint run method finished.")

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        logger.info(f"Running SuggestionBlueprint non-interactively with instruction: '{instruction[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        from agents import Runner
        import os
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
        try:
            for chunk in Runner.run(agent, instruction):
                yield chunk
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

if __name__ == "__main__":
    print("[SuggestionBlueprint] Example blueprint is running!")
    print("This is a visible demo output. The blueprint is operational.")
    SuggestionBlueprint.main()
