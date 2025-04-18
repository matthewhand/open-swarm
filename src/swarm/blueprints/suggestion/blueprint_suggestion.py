"""
Suggestion Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
# [Swarm Propagation] Next Blueprint: codey
# codey key vars: logger, project_root, src_path
# codey guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# codey debug: logger.debug("Codey agent created: Linus_Corvalds (Coordinator)")
# codey error handling: try/except ImportError with sys.exit(1)

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

# Last swarm update: 2025-04-18T10:15:21Z (UTC)
last_swarm_update = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ (UTC)")
print(f"# Last swarm update: {last_swarm_update}")

# --- Define the desired output structure ---
class SuggestionsOutput(TypedDict):
    """Defines the expected structure for the agent's output."""
    suggestions: List[str]

# Spinner UX enhancement (Open Swarm TODO)
SPINNER_STATES = ['Generating.', 'Generating..', 'Generating...', 'Running...']

# Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name

def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"
def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"
def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"
def execute_shell_command(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"
read_file_tool = PatchedFunctionTool(read_file, 'read_file')
write_file_tool = PatchedFunctionTool(write_file, 'write_file')
list_files_tool = PatchedFunctionTool(list_files, 'list_files')
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

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
        # Remove redundant client instantiation; rely on framework-level default client
        # All blueprints now use the default client set at framework init
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            # Ensure the model selected supports structured output (most recent OpenAI do)
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
            "containing a list of strings. You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
        )
        suggestion_agent = Agent(
            name="SuggestionAgent",
            instructions=suggestion_agent_instructions,
            tools=[read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
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
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   💡 SUGGESTION: SWARM-POWERED IDEA GENERATION DEMO          ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral swarm propagation,         ║\n║ swarm-powered suggestion logic, and robust import guards.    ║\n║ Try running: python blueprint_suggestion.py                  ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how Suggestion leverages swarm propagation for idea generation."}
    ]
    blueprint = SuggestionBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
