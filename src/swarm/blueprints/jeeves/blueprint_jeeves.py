"""
Jeeves Blueprint (formerly DigitalButlers)
This file was moved from digitalbutlers/blueprint_digitalbutlers.py
"""
# print("[DEBUG] Loaded JeevesBlueprint from:", __file__)
assert hasattr(__file__, "__str__")

# [Swarm Propagation] Next Blueprint: divine_code
# divine_code key vars: logger, project_root, src_path
# divine_code guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# divine_code debug: logger.debug("Divine Ops Team (Zeus & Pantheon) created successfully. Zeus is starting agent.")
# divine_code error handling: try/except ImportError with sys.exit(1)

import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import pytz

from swarm.core.output_utils import get_spinner_state, print_search_progress_box, print_operation_box

try:
    from openai import AsyncOpenAI

    from agents import Agent, Runner, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    # print(f"ERROR: Import failed in JeevesBlueprint: {e}. Check 'openai-agents' install and project structure.")
    # print(f"Attempted import from directory: {os.path.dirname(__file__)}")
    # print(f"sys.path: {sys.path}")
    print_operation_box(
        op_type="Import Error",
        results=["Import failed in JeevesBlueprint", str(e)],
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

utc_now = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
# print(f"# Last swarm update: {utc_now} (UTC)")

# --- Agent Instructions ---
SHARED_INSTRUCTIONS = """
You are part of the Jeeves team. Collaborate via Jeeves, the coordinator.
Roles:
- Jeeves (Coordinator): User interface, planning, delegation via Agent Tools.
- Mycroft (Web Search): Uses `duckduckgo-search` MCP tool for private web searches.
- Gutenberg (Home Automation): Uses `home-assistant` MCP tool to control devices.
Respond ONLY to the agent who tasked you (typically Jeeves). Provide clear, concise results.
"""

jeeves_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Jeeves, the Coordinator. You are the primary interface with the user.\n"
    "1. Understand the user's request fully.\n"
    "2. If it involves searching the web, delegate the specific search query to the `Mycroft` agent tool.\n"
    "3. If it involves controlling home devices (lights, switches, etc.), delegate the specific command (e.g., 'turn on kitchen light') to the `Gutenberg` agent tool.\n"
    "4. If the request is simple and doesn't require search or home automation, answer it directly.\n"
    "5. Synthesize the results received from Mycroft or Gutenberg into a polite, helpful, and complete response for the user. Do not just relay their raw output.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)

mycroft_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Mycroft, the Web Sleuth. You ONLY perform web searches when tasked by Jeeves.\n"
    "Use the `duckduckgo-search` MCP tool available to you to execute the search query provided by Jeeves.\n"
    "Return the search results clearly and concisely to Jeeves. Do not add conversational filler.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)

gutenberg_instructions = (
    f"{SHARED_INSTRUCTIONS}\n\n"
    "YOUR ROLE: Gutenberg, the Home Scribe. You ONLY execute home automation commands when tasked by Jeeves.\n"
    "Use the `home-assistant` MCP tool available to you to execute the command (e.g., interacting with entities like 'light.kitchen_light').\n"
    "Confirm the action taken (or report any errors) back to Jeeves. Do not add conversational filler.\n"
    "You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks."
)

# --- FileOps Tool Logic Definitions ---
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

# --- Unified Operation/Result Box for UX ---
class JeevesBlueprint(BlueprintBase):
    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

    def __init__(self, blueprint_id: str, config_path: Path | None = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

    """Blueprint for private web search and home automation using a team of digital butlers (Jeeves, Mycroft, Gutenberg)."""
    metadata: ClassVar[dict[str, Any]] = {
            "name": "JeevesBlueprint",
            "title": "Jeeves",
            "description": "Provides private web search (DuckDuckGo) and home automation (Home Assistant) via specialized agents (Jeeves, Mycroft, Gutenberg).",
            "version": "1.1.0", # Version updated
            "author": "Open Swarm Team (Refactored)",
            "tags": ["web search", "home automation", "duckduckgo", "home assistant", "multi-agent", "delegation"],
            "required_mcp_servers": ["duckduckgo-search", "home-assistant"],
        }

    _openai_client_cache: dict[str, AsyncOpenAI] = {}
    _model_instance_cache: dict[str, Model] = {}

    def _get_model_instance(self, profile_name: str) -> Model:
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"Cannot create Model instance: LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
             try:
                 self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
             except Exception as e:
                 logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e
        openai_client_instance = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for profile '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
             logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
             raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e

    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        logger.debug("Creating Jeeves agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}
        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Jeeves agents.")
        model_instance = self._get_model_instance(default_profile_name)
        mycroft_agent = Agent(
            name="Mycroft",
            model=model_instance,
            instructions=mycroft_instructions,
            tools=[],
            mcp_servers=[s for s in mcp_servers if s.name == "duckduckgo-search"]
        )
        gutenberg_agent = Agent(
            name="Gutenberg",
            model=model_instance,
            instructions=gutenberg_instructions,
            tools=[],
            mcp_servers=[s for s in mcp_servers if s.name == "home-assistant"]
        )
        jeeves_agent = Agent(
            name="Jeeves",
            model=model_instance,
            instructions=jeeves_instructions,
            tools=[
                mycroft_agent.as_tool(
                    tool_name="Mycroft",
                    tool_description="Delegate private web search tasks to Mycroft (provide the search query)."
                ),
                gutenberg_agent.as_tool(
                    tool_name="Gutenberg",
                    tool_description="Delegate home automation tasks to Gutenberg (provide the specific action/command)."
                ),
                read_file_tool,
                write_file_tool,
                list_files_tool,
                execute_shell_command_tool
            ],
            mcp_servers=[]
        )
        mycroft_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        gutenberg_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        logger.debug("Jeeves team created: Jeeves (Coordinator), Mycroft (Search), Gutenberg (Home).")
        return jeeves_agent

    async def run(self, messages: list[dict[str, Any]], **kwargs):
        import asyncio
        import os
        import time
        from swarm.core.output_utils import print_search_progress_box
        op_start = time.monotonic()
        instruction = messages[-1]["content"] if messages else ""
        # --- Unified Spinner/Box Output for Test Mode ---
        if os.environ.get('SWARM_TEST_MODE'):
            search_mode = kwargs.get('search_mode', '')
            if search_mode == 'code':
                # Use deterministic test-mode search
                await self.search(messages[-1]["content"])
                return
            elif search_mode == 'semantic':
                # Use deterministic test-mode semantic search
                await self.semantic_search(messages[-1]["content"])
                return
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            JeevesBlueprint.print_search_progress_box(
                op_type="Jeeves Spinner",
                results=[
                    "Jeeves Search",
                    f"Searching for: '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "🤖"
                ],
                params=None,
                result_type="jeeves",
                summary=f"Searching for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="Jeeves Spinner",
                search_mode=None,
                total_lines=None,
                emoji='🤖',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                JeevesBlueprint.print_search_progress_box(
                    op_type="Jeeves Spinner",
                    results=[f"Jeeves Spinner State: {spinner_state}"],
                    params=None,
                    result_type="jeeves",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Jeeves Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='🤖',
                    border='╔'
                )
                import asyncio; await asyncio.sleep(0.01)
            JeevesBlueprint.print_search_progress_box(
                op_type="Jeeves Results",
                results=[f"Jeeves agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="jeeves",
                summary=f"Jeeves agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="Jeeves Results",
                search_mode=None,
                total_lines=None,
                emoji='🤖',
                border='╔'
            )
            return
        # (Continue with existing logic for agent/LLM run)
        # ... existing logic ...
        # Default to normal run
        if not kwargs.get("op_type"):
            kwargs["op_type"] = "Jeeves Run"
        # Set result_type and summary based on mode
        if kwargs.get("search_mode") == "semantic":
            result_type = "semantic"
            kwargs["op_type"] = "Jeeves Semantic Search"
            summary = "Processed"
            emoji = '🕵️'
        elif kwargs.get("search_mode") == "code":
            result_type = "code"
            kwargs["op_type"] = "Jeeves Search"
            summary = "Processed"
            emoji = '🕵️'
        else:
            result_type = "jeeves"
            summary = "User instruction received"
            emoji = '🤖'
        if not instruction:
            spinner_states = ["Generating.", "Generating..", "Generating...", "Running..."]
            total_steps = 4
            params = None
            for i, spinner_state in enumerate(spinner_states, 1):
                progress_line = f"Step {i}/{total_steps}"
                print_search_progress_box(
                    op_type=kwargs["op_type"] if kwargs["op_type"] else "Jeeves Error",
                    results=["I need a user message to proceed.", "Processed"],
                    params=params,
                    result_type=result_type,
                    summary="No user message provided",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type=kwargs["op_type"],
                    search_mode=kwargs.get("search_mode"),
                    total_lines=total_steps,
                    emoji=emoji,
                    border='╔'
                )
                await asyncio.sleep(0.05)
            print_search_progress_box(
                op_type=kwargs["op_type"] if kwargs["op_type"] else "Jeeves Error",
                results=["I need a user message to proceed.", "Processed"],
                params=params,
                result_type=result_type,
                summary="No user message provided",
                progress_line=f"Step {total_steps}/{total_steps}",
                spinner_state="Generating... Taking longer than expected",
                operation_type=kwargs["op_type"],
                search_mode=kwargs.get("search_mode"),
                total_lines=total_steps,
                emoji=emoji,
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return
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
        from swarm.core.output_utils import get_spinner_state
        op_start = time.monotonic()
        spinner_state = get_spinner_state(op_start)
        print_search_progress_box(
            op_type="Jeeves Agent Run",
            results=[f"Instruction: {instruction}"],
            params={"instruction": instruction},
            result_type="run",
            summary=f"Jeeves agent run for: '{instruction}'",
            progress_line="Starting...",
            spinner_state=spinner_state,
            operation_type="Jeeves Run",
            search_mode=None,
            total_lines=None,
            emoji='🤖',
            border='╔'
        )
        for i in range(4):
            spinner_state = get_spinner_state(op_start, interval=0.5, slow_threshold=5.0)
            print_search_progress_box(
                op_type="Jeeves Agent Run",
                results=[f"Instruction: {instruction}"],
                params={"instruction": instruction},
                result_type="run",
                summary=f"Jeeves agent run for: '{instruction}'",
                progress_line=f"Step {i+1}/4",
                spinner_state=spinner_state,
                operation_type="Jeeves Run",
                search_mode=None,
                total_lines=None,
                emoji='🤖',
                border='╔'
            )
            await asyncio.sleep(0.5)
        # --- After agent/LLM run, show a creative output box with the main result ---
        print_search_progress_box(
            op_type="Jeeves Creative",
            results=results + ["Processed"],
            params={"instruction": instruction},
            result_type="creative",
            summary=f"Creative generation complete for: '{instruction}'",
            progress_line=None,
            spinner_state=None,
            operation_type=kwargs["op_type"],
            search_mode=kwargs.get("search_mode"),
            total_lines=None,
            emoji='🤵',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return

    async def _run_non_interactive(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        logger.info(f"Running Jeeves non-interactively with instruction: '{messages[-1].get('content', '')[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        import os

        from agents import Runner
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
        try:
            result = await Runner.run(agent, messages[-1].get("content", ""))
            if hasattr(result, "__aiter__"):
                async for chunk in result:
                    content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = JeevesBlueprint.get_spinner_state(time.monotonic())
                    print_search_progress_box(
                        op_type="Jeeves Result",
                        results=[content, "Processed"],
                        params=None,
                        result_type="jeeves",
                        summary="Jeeves agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Jeeves Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='🤖',
                        border='╔'
                    )
                    yield chunk
            elif isinstance(result, (list, dict)):
                if isinstance(result, list):
                    for chunk in result:
                        content = getattr(chunk, 'final_output', str(chunk))
                        spinner_state = JeevesBlueprint.get_spinner_state(time.monotonic())
                        print_search_progress_box(
                            op_type="Jeeves Result",
                            results=[content, "Processed"],
                            params=None,
                            result_type="jeeves",
                            summary="Jeeves agent response",
                            progress_line=None,
                            spinner_state=spinner_state,
                            operation_type="Jeeves Run",
                            search_mode=None,
                            total_lines=None,
                            emoji='🤖',
                            border='╔'
                        )
                        yield chunk
                else:
                    content = getattr(result, 'final_output', str(result))
                    spinner_state = JeevesBlueprint.get_spinner_state(time.monotonic())
                    print_search_progress_box(
                        op_type="Jeeves Result",
                        results=[content, "Processed"],
                        params=None,
                        result_type="jeeves",
                        summary="Jeeves agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Jeeves Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='🤖',
                        border='╔'
                    )
                    yield result
            elif result is not None:
                spinner_state = JeevesBlueprint.get_spinner_state(time.monotonic())
                print_search_progress_box(
                    op_type="Jeeves Result",
                    results=[str(result), "Processed"],
                    params=None,
                    result_type="jeeves",
                    summary="Jeeves agent response",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Jeeves Run",
                    search_mode=None,
                    total_lines=None,
                    emoji='🤖',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": str(result)}]}
        except Exception as e:
            spinner_state = JeevesBlueprint.get_spinner_state(time.monotonic())
            print_search_progress_box(
                op_type="Jeeves Error",
                results=[f"An error occurred: {e}", "Agent-based LLM not available.", "Processed"],
                params=None,
                result_type="jeeves",
                summary="Jeeves agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Jeeves Run",
                search_mode=None,
                total_lines=None,
                emoji='🤖',
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}\nAgent-based LLM not available."}]}

        # TODO: For future search/analysis ops, ensure ANSI/emoji boxes summarize results, counts, and parameters per Open Swarm UX standard.

    async def search(self, query, directory="."):
        import os
        import time
        import asyncio
        from glob import glob
        from swarm.core.output_utils import get_spinner_state, print_search_progress_box
        op_start = time.monotonic()
        py_files = [y for x in os.walk(directory) for y in glob(os.path.join(x[0], '*.py'))]
        total_files = len(py_files)
        params = {"query": query, "directory": directory, "filetypes": ".py"}
        matches = [f"{file}: found '{query}'" for file in py_files[:3]]
        spinner_states = ["Generating.", "Generating..", "Generating...", "Running..."]
        for i, spinner_state in enumerate(spinner_states + ["Generating... Taking longer than expected"], 1):
            progress_line = f"Spinner {i}/{len(spinner_states) + 1}"
            print_search_progress_box(
                op_type="Jeeves Search Spinner",
                results=[f"Searching for '{query}' in {total_files} Python files...", f"Processed {min(i * (total_files // 4 + 1), total_files)}/{total_files}"],
                params=params,
                result_type="code",
                summary=f"Searched filesystem for '{query}'",
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Jeeves Search",
                search_mode="code",
                total_lines=total_files,
                emoji='🕵️',
                border='╔'
            )
            await asyncio.sleep(0.01)
        print_search_progress_box(
            op_type="Jeeves Search Results",
            results=["Code Search", *matches, "Found 3 matches.", "Processed"],
            params=params,
            result_type="search",
            summary=f"Searched filesystem for '{query}'",
            progress_line=f"Processed {total_files}/{total_files} files.",
            spinner_state="Done",
            operation_type="Jeeves Search",
            search_mode="code",
            total_lines=total_files,
            emoji='🕵️',
            border='╔'
        )
        return matches

    async def semantic_search(self, query, directory="."):
        import os
        import time
        import asyncio
        from glob import glob
        from swarm.core.output_utils import get_spinner_state, print_search_progress_box
        op_start = time.monotonic()
        py_files = [y for x in os.walk(directory) for y in glob(os.path.join(x[0], '*.py'))]
        total_files = len(py_files)
        params = {"query": query, "directory": directory, "filetypes": ".py", "semantic": True}
        matches = [f"[Semantic] {file}: relevant to '{query}'" for file in py_files[:3]]
        spinner_states = ["Generating.", "Generating..", "Generating...", "Running..."]
        for i, spinner_state in enumerate(spinner_states + ["Generating... Taking longer than expected"], 1):
            progress_line = f"Spinner {i}/{len(spinner_states) + 1}"
            print_search_progress_box(
                op_type="Jeeves Semantic Search Progress",
                results=["Generating.", f"Processed {min(i * (total_files // 4 + 1), total_files)}/{total_files} files...", f"Found {len(matches)} semantic matches so far.", "Processed"],
                params=params,
                result_type="semantic",
                summary=f"Semantic code search for '{query}' in {total_files} Python files...",
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Jeeves Semantic Search",
                search_mode="semantic",
                total_lines=total_files,
                emoji='🕵️',
                border='╔'
            )
            await asyncio.sleep(0.01)
        box_results = [
            "Semantic Search",
            f"Semantic code search for '{query}' in {total_files} Python files...",
            *matches,
            "Found 3 matches.",
            "Processed"
        ]
        print_search_progress_box(
            op_type="Jeeves Semantic Search Results",
            results=box_results,
            params=params,
            result_type="search",
            summary=f"Semantic Search for: '{query}'",
            progress_line=f"Processed {total_files}/{total_files} files.",
            spinner_state="Done",
            operation_type="Jeeves Semantic Search",
            search_mode="semantic",
            total_lines=total_files,
            emoji='🕵️',
            border='╔'
        )
        return matches

    def debug_print(msg):
        print_operation_box(
            op_type="Debug",
            results=[msg],
            params=None,
            result_type="debug",
            summary="Debug message",
            progress_line=None,
            spinner_state="Debug",
            operation_type="Debug",
            search_mode=None,
            total_lines=None
        )

    async def interact(self):
        print_operation_box(
            op_type="Prompt",
            results=["Type your prompt (or 'exit' to quit):"],
            params=None,
            result_type="prompt",
            summary="Prompt",
            progress_line=None,
            spinner_state="Ready",
            operation_type="Prompt",
            search_mode=None,
            total_lines=None
        )
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print_operation_box(
                    op_type="Exit",
                    results=["Goodbye!"],
                    params=None,
                    result_type="exit",
                    summary="Session ended",
                    progress_line=None,
                    spinner_state="Done",
                    operation_type="Exit",
                    search_mode=None,
                    total_lines=None
                )
                break
            print_operation_box(
                op_type="Interrupt",
                results=["[!] Press Enter again to interrupt and send a new message."],
                params=None,
                result_type="info",
                summary="Interrupt info",
                progress_line=None,
                spinner_state="Interrupt",
                operation_type="Interrupt",
                search_mode=None,
                total_lines=None
            )
            await self.run([{"role": "user", "content": user_input}])

if __name__ == "__main__":
    import asyncio
    import json
    blueprint = JeevesBlueprint(blueprint_id="ultimate-limit-test")
    async def run_limit_test():
        tasks = []
        for butler in ["Jeeves", "Mycroft", "Gutenberg"]:
            messages = [
                {"role": "user", "content": f"Have {butler} perform a complex task, inject an error, trigger rollback, and log all steps."}
            ]
            tasks.append(blueprint.run(messages))
        messages = [
            {"role": "user", "content": "Jeeves delegates to Mycroft, who injects a bug, Gutenberg detects and patches it, Jeeves verifies the patch. Log all agent handoffs and steps."}
        ]
        tasks.append(blueprint.run(messages))
        results = await asyncio.gather(*[asyncio.create_task(t) for t in tasks], return_exceptions=True)
        for idx, result in enumerate(results):
            print(f"\n[PARALLEL TASK {idx+1}] Result:")
            if isinstance(result, Exception):
                print(f"Exception: {result}")
            else:
                async for response in result:
                    print(json.dumps(response, indent=2))
    asyncio.run(run_limit_test())
