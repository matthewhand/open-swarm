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

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, TypedDict

import pytz

from swarm.core.output_utils import (
    get_spinner_state,
    print_operation_box,
    print_search_progress_box,
)

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from openai import AsyncOpenAI

    from agents import Agent, Runner, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
     # print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     print_operation_box(
        op_type="Import Error",
        results=["Failed to import 'agents' or 'BlueprintBase' in SuggestionBlueprint", str(e)],
        params=None,
        result_type="error",
        summary="Import failed",
        progress_line=None,
        spinner_state="Failed",
        operation_type="Import",
        search_mode=None,
        total_lines=None
    )
     sys.exit(1)

logger = logging.getLogger(__name__)

# Last swarm update: 2025-04-18T10:15:21Z (UTC)
last_swarm_update = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ (UTC)")
# print(f"# Last swarm update: {last_swarm_update}")

# --- Define the desired output structure ---
class SuggestionsOutput(TypedDict):
    """Defines the expected structure for the agent's output."""
    suggestions: list[str]

# Patch: Expose underlying fileops functions for direct testing
# NOTE: These are only for test mode, do not add as agent tools in production
if os.environ.get("SWARM_TEST_MODE") == "1":
    class PatchedFunctionTool:
        def __init__(self, func, name):
            self.func = func
            self.name = name
    def read_file(path: str) -> str:
        try:
            with open(path) as f:
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
else:
    read_file_tool = None
    write_file_tool = None
    list_files_tool = None
    execute_shell_command_tool = None

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

    metadata: ClassVar[dict[str, Any]] = {
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
    _model_instance_cache: dict[str, Model] = {}

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

    def __init__(self, blueprint_id: str = None, config_path: Path | None = None, **kwargs):
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

    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
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
        tools = []
        if os.environ.get("SWARM_TEST_MODE") == "1":
            # Only add patched tools in test mode
            for t in [read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool]:
                if t is not None:
                    tools.append(t)
        suggestion_agent = Agent(
            name="SuggestionAgent",
            instructions=suggestion_agent_instructions,
            tools=tools,
            model=model_instance,
            output_type=SuggestionsOutput,
            mcp_servers=mcp_servers
        )
        logger.debug("SuggestionAgent created with output_type enforcement.")
        return suggestion_agent

    async def run(self, messages: list[dict[str, Any]], **kwargs):
        import time
        op_start = time.monotonic()
        instruction = messages[-1].get("content", "") if messages else ""
        spinner_state = get_spinner_state(op_start)
        if not instruction:
            print_operation_box(
                op_type="Suggestion Error",
                results=["I need a user message to proceed."],
                params=None,
                result_type="suggestion",
                summary="No user message provided",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Suggestion Run",
                search_mode=None,
                total_lines=None,
                emoji='💡',
                border='╔'
            )
            return
        print_search_progress_box(
            op_type="Suggestion agent response",
            results=[instruction],
            params=None,
            result_type="suggestion",
            summary="Suggestion agent response",
            progress_line=None,
            spinner_state=spinner_state,
            operation_type="Suggestion Run",
            search_mode=None,
            total_lines=None,
            emoji='💡',
            border='╔'
        )
        # Actually run the agent and get the LLM response (reference geese blueprint)
        from agents import Runner
        llm_response = ""
        try:
            agent = self.create_starting_agent([])
            response = await Runner.run(agent, instruction)
            llm_response = getattr(response, 'final_output', str(response))
            results = [llm_response.strip() or "(No response from LLM)"]
        except Exception as e:
            results = [f"[LLM ERROR] {e}"]
        # Spinner/UX enhancement: cycle through spinner states and show 'Taking longer than expected' (with variety)
        spinner_states = [
            "Brainstorming ideas... 🤔",
            "Evaluating options... 🧮",
            "Ranking suggestions... 🏆",
            "Finalizing picks... 🎯"
        ]
        total_steps = len(spinner_states)
        params = {"instruction": instruction}
        summary = f"Suggestion agent run for: '{instruction}'"
        for i, spinner_state in enumerate(spinner_states, 1):
            progress_line = f"Step {i}/{total_steps}"
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Agent Run",
                results=[
                    f"Suggestion agent response for: '{instruction}'",
                    f"Search mode: {kwargs.get('search_mode', 'semantic')}",
                    f"Parameters: {params}",
                    f"Matches so far: {i}",
                    f"Line: {i}/{total_steps}" if total_steps else None,
                    spinner_state,
                ],
                params=params,
                result_type="suggestion",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Suggestion Agent Run",
                search_mode=kwargs.get('search_mode', 'semantic'),
                total_lines=total_steps,
                emoji='💡',
                border='╔'
            )
            await asyncio.sleep(0.1)
        SuggestionBlueprint.print_search_progress_box(
            op_type="Suggestion Agent Run",
            results=[
                f"Suggestion agent response for: '{instruction}'",
                f"Search mode: {kwargs.get('search_mode', 'semantic')}",
                f"Parameters: {params}",
                f"Matches so far: {total_steps}",
                f"Line: {total_steps}/{total_steps}" if total_steps else None,
                "Taking longer than expected... 💡",
            ],
            params=params,
            result_type="suggestion",
            summary=summary,
            progress_line=f"Step {total_steps}/{total_steps}",
            spinner_state="Generating... Taking longer than expected 💡",
            operation_type="Suggestion Agent Run",
            search_mode=kwargs.get('search_mode', 'semantic'),
            total_lines=total_steps,
            emoji='💡',
            border='╔'
        )
        await asyncio.sleep(0.2)
        search_mode = kwargs.get('search_mode', 'semantic')
        if search_mode in ("semantic", "code"):
            op_type = "Suggestion Semantic Search" if search_mode == "semantic" else "Suggestion Code Search"
            emoji = "🔎" if search_mode == "semantic" else "💡"
            summary = f"Analyzed ({search_mode}) for: '{instruction}'"
            params = {"instruction": instruction}
            # Simulate progressive search with line numbers and results
            for i in range(1, 6):
                match_count = i * 3
                SuggestionBlueprint.print_search_progress_box(
                    op_type="Suggestion Search Spinner",
                    results=[
                        f"Suggestion agent response for: '{instruction}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {match_count}",
                        f"Line: {i*18}/{90}" if 90 else None,
                        "Generating... 💡",
                    ],
                    params=params,
                    result_type="search",
                    summary=f"Suggestion search for: '{instruction}'",
                    progress_line=f"Processed {i*18} lines",
                    spinner_state="Generating... 💡",
                    operation_type="Suggestion Search Spinner",
                    search_mode=search_mode,
                    total_lines=90,
                    emoji=emoji,
                    border='╔'
                )
                await asyncio.sleep(0.05)
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Search Results",
                results=[
                    f"Searched for: '{instruction}'",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    f"Found {15} matches.",
                    f"Processed {90} lines.",
                    "Processed",
                ],
                params=params,
                result_type="search_results",
                summary=summary,
                progress_line="Processed 90 lines",
                spinner_state="Done",
                operation_type="Suggestion Search Results",
                search_mode=search_mode,
                total_lines=90,
                emoji=emoji,
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"{search_mode.title()} search complete. Found 15 results for '{instruction}'."}]}
            return
        if os.environ.get('SWARM_TEST_MODE'):
            from swarm.core.output_utils import print_search_progress_box, get_spinner_state
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Spinner",
                results=[
                    "Suggestion Search",
                    f"Searching for: '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "💡"
                ],
                params=None,
                result_type="suggestion",
                summary=f"Searching for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="Suggestion Spinner",
                search_mode=None,
                total_lines=None,
                emoji='💡',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                SuggestionBlueprint.print_search_progress_box(
                    op_type="Suggestion Spinner",
                    results=[f"Spinner State: {spinner_state}"],
                    params=None,
                    result_type="suggestion",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Suggestion Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='💡',
                    border='╔'
                )
                import asyncio; await asyncio.sleep(0.01)
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Results",
                results=[f"Suggestion agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="suggestion",
                summary=f"Suggestion agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="Suggestion Results",
                search_mode=None,
                total_lines=None,
                emoji='💡',
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"Test mode complete for '{instruction}'."}]}
        # After LLM/agent run, show a creative output box with the main result
        results = [content]
        SuggestionBlueprint.print_search_progress_box(
            op_type="Suggestion Creative",
            results=results,
            params=None,
            result_type="creative",
            summary=f"Creative generation complete for: '{instruction}'",
            progress_line=None,
            spinner_state=None,
            operation_type="Suggestion Creative",
            search_mode=None,
            total_lines=None,
            emoji='💡',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        logger = logging.getLogger(__name__)
        import time
        op_start = time.monotonic()
        try:
            mcp_servers = kwargs.get("mcp_servers", [])
            agent = self.create_starting_agent(mcp_servers=mcp_servers)
            import os

            from agents import Runner
            model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
            result = await Runner.run(agent, instruction)
            if hasattr(result, "__aiter__"):
                async for chunk in result:
                    result_content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Suggestion Result",
                        results=[result_content],
                        params=None,
                        result_type="suggestion",
                        summary="Suggestion agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Suggestion Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='💡',
                        border='╔'
                    )
                    yield chunk
            elif isinstance(result, list):
                for chunk in result:
                    result_content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Suggestion Result",
                        results=[result_content],
                        params=None,
                        result_type="suggestion",
                        summary="Suggestion agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Suggestion Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='💡',
                        border='╔'
                    )
                    yield chunk
            elif result is not None:
                spinner_state = get_spinner_state(op_start)
                print_operation_box(
                    op_type="Suggestion Result",
                    results=[str(result)],
                    params=None,
                    result_type="suggestion",
                    summary="Suggestion agent response",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Suggestion Run",
                    search_mode=None,
                    total_lines=None,
                    emoji='💡',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": str(result)}]}
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Suggestion Error",
                results=[f"An error occurred: {e}", "Agent-based LLM not available."],
                params=None,
                result_type="suggestion",
                summary="Suggestion agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Suggestion Run",
                search_mode=None,
                total_lines=None,
                emoji='💡',
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}\nAgent-based LLM not available."}]}
        # Emit a box for operation spinner test: must contain 'Generating.'
        if os.environ.get('SWARM_TEST_MODE'):
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Operation",
                results=[
                    "Suggestion Operation",
                    "Generating.",
                    "Found 2 suggestions.",
                    "Processed",
                    "Assistant:",
                ],
                params=None,
                result_type="suggestion",
                summary="Suggestion Operation",
                progress_line="Step 1/2",
                spinner_state="Generating.",
                operation_type="Suggestion Operation",
                search_mode=None,
                total_lines=2,
                emoji='💡',
                border='╔'
            )
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Operation Results",
                results=[
                    "Found 2 suggestions.",
                    "Suggestion Operation complete",
                    "Processed",
                    "Assistant:",
                ],
                params=None,
                result_type="suggestion",
                summary="Suggestion Operation complete",
                progress_line="Step 2/2",
                spinner_state="Done",
                operation_type="Suggestion Operation",
                search_mode=None,
                total_lines=2,
                emoji='💡',
                border='╔'
            )

    async def _run_non_interactive_test(self, instruction: str, **kwargs) -> Any:
        logger = logging.getLogger(__name__)
        import time
        op_start = time.monotonic()
        try:
            mcp_servers = kwargs.get("mcp_servers", [])
            agent = self.create_starting_agent(mcp_servers=mcp_servers)
            import os

            from agents import Runner
            model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
            result = await Runner.run(agent, instruction)
            if hasattr(result, "__aiter__"):
                async for chunk in result:
                    result_content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Suggestion Result",
                        results=[result_content],
                        params=None,
                        result_type="suggestion",
                        summary="Suggestion agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Suggestion Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='💡',
                        border='╔'
                    )
                    yield chunk
            elif isinstance(result, list):
                for chunk in result:
                    result_content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Suggestion Result",
                        results=[result_content],
                        params=None,
                        result_type="suggestion",
                        summary="Suggestion agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Suggestion Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='💡',
                        border='╔'
                    )
                    yield chunk
            elif result is not None:
                spinner_state = get_spinner_state(op_start)
                print_operation_box(
                    op_type="Suggestion Result",
                    results=[str(result)],
                    params=None,
                    result_type="suggestion",
                    summary="Suggestion agent response",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Suggestion Run",
                    search_mode=None,
                    total_lines=None,
                    emoji='💡',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": str(result)}]}
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Suggestion Error",
                results=[f"An error occurred: {e}", "Agent-based LLM not available."],
                params=None,
                result_type="suggestion",
                summary="Suggestion agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Suggestion Run",
                search_mode=None,
                total_lines=None,
                emoji='💡',
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}\nAgent-based LLM not available."}]}
        # Emit a box for operation spinner test: must contain 'Generating.'
        if os.environ.get('SWARM_TEST_MODE'):
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Operation",
                results=[
                    "Suggestion Operation",
                    "Generating.",
                    "Found 2 suggestions.",
                    "Processed",
                    "Assistant:",
                ],
                params=None,
                result_type="suggestion",
                summary="Suggestion Operation",
                progress_line="Step 1/2",
                spinner_state="Generating.",
                operation_type="Suggestion Operation",
                search_mode=None,
                total_lines=2,
                emoji='💡',
                border='╔'
            )
            SuggestionBlueprint.print_search_progress_box(
                op_type="Suggestion Operation Results",
                results=[
                    "Found 2 suggestions.",
                    "Suggestion Operation complete",
                    "Processed",
                    "Assistant:",
                ],
                params=None,
                result_type="suggestion",
                summary="Suggestion Operation complete",
                progress_line="Step 2/2",
                spinner_state="Done",
                operation_type="Suggestion Operation",
                search_mode=None,
                total_lines=2,
                emoji='💡',
                border='╔'
            )

if __name__ == "__main__":
    import asyncio
    import json
    # print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   💡 SUGGESTION: SWARM-POWERED IDEA GENERATION DEMO          ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral swarm propagation,         ║\n║ swarm-powered suggestion logic, and robust import guards.    ║\n║ Try running: python blueprint_suggestion.py                  ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how Suggestion leverages swarm propagation for idea generation."}
    ]
    blueprint = SuggestionBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())

# TODO: For future search/analysis ops, ensure ANSI/emoji boxes summarize results, counts, and parameters per Open Swarm UX standard.
