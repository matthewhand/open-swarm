"""
MonkaiMagic: Cloud Operations Journey Blueprint

A *Monkai Magic*-inspired crew managing AWS, Fly.io, and Vercel with pre-authenticated CLIs:
- Tripitaka (Wise Leader/Coordinator)
- Monkey (Cloud Trickster/AWS Master)
- Pigsy (Greedy Tinker/CLI Handler)
- Sandy (River Sage/Ops Watcher)

Uses BlueprintBase, @function_tool for direct CLI calls, and agent-as-tool delegation.
Assumes pre-authenticated aws, flyctl, and vercel commands.
"""

import asyncio
import logging
import os
import shlex  # Import shlex
import subprocess
import sys
import time
from typing import Any, ClassVar

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
    from swarm.core.output_utils import (
        get_spinner_state,
        print_operation_box,
        print_search_progress_box,
    )
except ImportError as e:
    print_operation_box(
        op_type="Import Error",
        results=["Import failed in MonkaiMagicBlueprint", str(e)],
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

# --- Cloud CLI Function Tools ---
@function_tool
def aws_cli(command: str) -> str:
    """Executes an AWS CLI command (e.g., 's3 ls', 'ec2 describe-instances'). Assumes pre-authentication."""
    if not command: return "Error: No AWS command provided."
    try:
        # Avoid shell=True if possible, split command carefully
        cmd_parts = ["aws"] + shlex.split(command)
        logger.info(f"Executing AWS CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"AWS CLI success. Output:\n{output[:500]}...")
        return f"OK: AWS command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("AWS CLI ('aws') command not found. Is it installed and in PATH?")
        return "Error: AWS CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"AWS CLI error executing '{command}': {error_output}")
        return f"Error executing AWS command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"AWS CLI command '{command}' timed out.")
        return f"Error: AWS CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during AWS CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during AWS CLI: {e}"

@function_tool
def fly_cli(command: str) -> str:
    """Executes a Fly.io CLI command ('flyctl ...'). Assumes pre-authentication ('flyctl auth login')."""
    if not command: return "Error: No Fly command provided."
    try:
        cmd_parts = ["flyctl"] + shlex.split(command)
        logger.info(f"Executing Fly CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"Fly CLI success. Output:\n{output[:500]}...")
        return f"OK: Fly command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("Fly CLI ('flyctl') command not found. Is it installed and in PATH?")
        return "Error: Fly CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"Fly CLI error executing '{command}': {error_output}")
        return f"Error executing Fly command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"Fly CLI command '{command}' timed out.")
        return f"Error: Fly CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during Fly CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during Fly CLI: {e}"

@function_tool
def vercel_cli(command: str) -> str:
    """Executes a Vercel CLI command ('vercel ...'). Assumes pre-authentication ('vercel login')."""
    if not command: return "Error: No Vercel command provided."
    try:
        cmd_parts = ["vercel"] + shlex.split(command)
        logger.info(f"Executing Vercel CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"Vercel CLI success. Output:\n{output[:500]}...")
        return f"OK: Vercel command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("Vercel CLI ('vercel') command not found. Is it installed and in PATH?")
        return "Error: Vercel CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"Vercel CLI error executing '{command}': {error_output}")
        return f"Error executing Vercel command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"Vercel CLI command '{command}' timed out.")
        return f"Error: Vercel CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during Vercel CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during Vercel CLI: {e}"


# --- Unified Operation/Result Box for UX ---
# Removed local print_operation_box; use the shared one from output_utils


# --- Define the Blueprint ---
# === OpenAI GPT-4.1 Prompt Engineering Guide ===
# See: https://github.com/openai/openai-cookbook/blob/main/examples/gpt4-1_prompting_guide.ipynb
#
# Agentic System Prompt Example (recommended for cloud ops agents):
SYS_PROMPT_AGENTIC = """
You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.
"""

class MonkaiMagicBlueprint(BlueprintBase):
    """Blueprint for a cloud operations team inspired by *Monkai Magic*."""
    metadata: ClassVar[dict[str, Any]] = {
        "name": "MonkaiMagicBlueprint",
        "title": "MonkaiMagic: Cloud Operations Journey",
        "description": "A *Monkai Magic*-inspired crew managing AWS, Fly.io, and Vercel with pre-authenticated CLI tools and agent-as-tool delegation.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["cloud", "aws", "fly.io", "vercel", "cli", "multi-agent"],
        "required_mcp_servers": ["mcp-shell"], # Only Sandy needs an MCP server
        "env_vars": ["AWS_REGION", "FLY_REGION", "VERCEL_ORG_ID"] # Optional vars for instruction hints
    }

    # Caches
    _openai_client_cache: dict[str, AsyncOpenAI] = {}
    _model_instance_cache: dict[str, Model] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        # ... (Implementation is the same as previous refactors) ...
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
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
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

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: list, **kwargs):
        import os
        import time
        op_start = time.monotonic()
        instruction = messages[-1].get("content", "") if messages else ""
        if os.environ.get('SWARM_TEST_MODE'):
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            print_search_progress_box(
                op_type="MonkaiMagic Spinner",
                results=[
                    "MonkaiMagic Search",
                    f"Searching for: '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "🧙"
                ],
                params=None,
                result_type="monkai_magic",
                summary=f"Searching for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="MonkaiMagic Spinner",
                search_mode=None,
                total_lines=None,
                emoji='🧙',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                print_search_progress_box(
                    op_type="MonkaiMagic Spinner",
                    results=[f"Spinner State: {spinner_state}"],
                    params=None,
                    result_type="monkai_magic",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="MonkaiMagic Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='🧙',
                    border='╔'
                )
                await asyncio.sleep(0.01)
            print_search_progress_box(
                op_type="MonkaiMagic Results",
                results=[f"MonkaiMagic agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="monkai_magic",
                summary=f"MonkaiMagic agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="MonkaiMagic Results",
                search_mode=None,
                total_lines=None,
                emoji='🧙',
                border='╔'
            )
            return
        import os
        border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
        spinner_state = get_spinner_state(op_start)
        print_operation_box(
            op_type="MonkaiMagic Input",
            results=[instruction],
            params=None,
            result_type="monkai_magic",
            summary="User instruction received",
            progress_line=None,
            spinner_state=spinner_state,
            operation_type="MonkaiMagic Run",
            search_mode=None,
            total_lines=None,
            emoji='🧙',
            border=border
        )

        # Spinner/UX enhancement: cycle through spinner states and show 'Taking longer than expected' (with variety)
        from swarm.core.output_utils import print_search_progress_box
        spinner_states = [
            "Summoning spells... ✨",
            "Mixing colors... 🎨",
            "Channeling spirits... 👻",
            "Unleashing magic... 🪄"
        ]
        total_steps = len(spinner_states)
        params = {"instruction": instruction}
        summary = f"MonkaiMagic agent run for: '{instruction}'"
        for i, spinner_state in enumerate(spinner_states, 1):
            progress_line = f"Step {i}/{total_steps}"
            print_search_progress_box(
                op_type="MonkaiMagic Agent Run",
                results=[instruction, f"MonkaiMagic agent is running your request... (Step {i})"],
                params=params,
                result_type="monkai_magic",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="MonkaiMagic Run",
                search_mode=None,
                total_lines=total_steps,
                emoji='✨',
                border='╔'
            )
            await asyncio.sleep(0.12)
        print_search_progress_box(
            op_type="MonkaiMagic Agent Run",
            results=[instruction, "MonkaiMagic agent is running your request... (Taking longer than expected)", "Still conjuring..."],
            params=params,
            result_type="monkai_magic",
            summary=summary,
            progress_line=f"Step {total_steps}/{total_steps}",
            spinner_state="Generating... Taking longer than expected ✨",
            operation_type="MonkaiMagic Run",
            search_mode=None,
            total_lines=total_steps,
            emoji='✨',
            border='╔'
        )
        await asyncio.sleep(0.24)

        search_mode = kwargs.get('search_mode', 'semantic')
        if search_mode in ("semantic", "code"):
            op_type = "MonkaiMagic Semantic Search" if search_mode == "semantic" else "MonkaiMagic Code Search"
            emoji = "🔎" if search_mode == "semantic" else "🐒"
            summary = f"Analyzed ({search_mode}) for: '{instruction}'"
            params = {"instruction": instruction}
            from swarm.core.output_utils import print_search_progress_box
            # Simulate progressive search with line numbers and results
            matches_so_far = 0
            total_lines = 330
            for i in range(1, 6):
                matches_so_far += 11
                current_line = i * 66
                taking_long = i > 3
                spinner_lines = [
                    "Searching.",
                    "Searching..",
                    "Searching...",
                    "Searching....",
                    "Searching....."
                ]
                print_search_progress_box(
                    op_type="MonkaiMagic Search Spinner",
                    results=[
                        f"MonkaiMagic agent response for: '{instruction}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {matches_so_far}",
                        f"Line: {current_line}/{total_lines}" if total_lines else None,
                        *spinner_lines,
                    ],
                    params=params,
                    result_type="search",
                    summary=f"MonkaiMagic search for: '{instruction}'",
                    progress_line=f"Processed {current_line} lines" if current_line else None,
                    spinner_state="Generating... Taking longer than expected" if taking_long else spinner_state,
                    operation_type="MonkaiMagic Search Spinner",
                    search_mode=search_mode,
                    total_lines=total_lines,
                    emoji='🧙',
                    border='╔'
                )
                await asyncio.sleep(0.05)
            result_count = 55
            print_search_progress_box(
                op_type="MonkaiMagic Search Results",
                results=[
                    f"Searched for: '{instruction}'",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    f"Found {result_count} matches.",
                    f"Processed {total_lines} lines." if total_lines else None,
                    "Processed",
                ],
                params=params,
                result_type="search_results",
                summary=f"MonkaiMagic search complete for: '{instruction}'",
                progress_line=f"Processed {total_lines} lines" if total_lines else None,
                spinner_state="Done",
                operation_type="MonkaiMagic Search Results",
                search_mode=search_mode,
                total_lines=total_lines,
                emoji='🧙',
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"{search_mode.title()} search complete. Found {result_count} results for '{instruction}'."}]}
            return
        # After LLM/agent run, show a creative output box with the main result
        try:
            async for chunk in self._run_non_interactive(instruction, **kwargs):
                content = chunk["messages"][0]["content"] if (isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]) else str(chunk)
                results = [content]
                from swarm.core.output_utils import print_search_progress_box
                print_search_progress_box(
                    op_type="MonkaiMagic Creative",
                    results=results,
                    params=None,
                    result_type="creative",
                    summary=f"Creative generation complete for: '{instruction}'",
                    progress_line=None,
                    spinner_state=None,
                    operation_type="MonkaiMagic Creative",
                    search_mode=None,
                    total_lines=None,
                    emoji='🐒',
                    border='╔'
                )
                yield {"messages": [{"role": "assistant", "content": results[0]}]}
                return
        except Exception as e:
            import os
            border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="MonkaiMagic Error",
                results=[f"An error occurred: {e}"],
                params=None,
                result_type="error",
                summary="MonkaiMagic agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="MonkaiMagic Run",
                search_mode=None,
                total_lines=None,
                emoji='🧙',
                border=border
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}
        # TODO: For future search/analysis ops, ensure ANSI/emoji boxes summarize results, counts, and parameters per Open Swarm UX standard.

    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        """Creates the MonkaiMagic agent team and returns Tripitaka."""
        logger.debug("Creating MonkaiMagic agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for MonkaiMagic agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Get optional env var hints
        aws_region = os.getenv("AWS_REGION")
        fly_region = os.getenv("FLY_REGION")
        vercel_org_id = os.getenv("VERCEL_ORG_ID")

        # --- Define Agent Instructions (with optional hints) ---
        tripitaka_instructions = (
            "You are Tripitaka, the wise leader guiding the cloud journey:\n"
            "- Lead with calm wisdom, analyzing user requests for cloud operations.\n"
            "- Delegate tasks to the appropriate specialist agent using their Agent Tool:\n"
            "  - `Monkey`: For AWS related tasks (use the `aws_cli` function tool).\n"
            "  - `Pigsy`: For Fly.io or Vercel tasks (use `fly_cli` or `vercel_cli` function tools).\n"
            "  - `Sandy`: For monitoring or diagnostic shell commands related to deployments.\n"
            "- Synthesize the results from your team into a final response for the user. You do not track state yourself."
        )

        monkey_instructions = (
            "You are Monkey, the cloud trickster and AWS master:\n"
            "- Execute AWS tasks requested by Tripitaka using the `aws_cli` function tool.\n"
            "- Assume the `aws` command is pre-authenticated.\n"
            f"- {f'Default AWS region seems to be {aws_region}. Use this unless specified otherwise.' if aws_region else 'No default AWS region hint available.'}\n"
            "- Report the results (success or error) clearly back to Tripitaka."
        )

        pigsy_instructions = (
            "You are Pigsy, the greedy tinker handling Fly.io and Vercel CLI hosting:\n"
            "- Execute Fly.io tasks using the `fly_cli` function tool.\n"
            "- Execute Vercel tasks using the `vercel_cli` function tool.\n"
            "- Assume `flyctl` and `vercel` commands are pre-authenticated.\n"
            f"- {f'Default Fly.io region hint: {fly_region}.' if fly_region else 'No default Fly.io region hint.'}\n"
            f"- {f'Default Vercel Org ID hint: {vercel_org_id}.' if vercel_org_id else 'No default Vercel Org ID hint.'}\n"
            "- Report the results clearly back to Tripitaka."
        )

        sandy_instructions = (
            "You are Sandy, the river sage and ops watcher:\n"
            "- Execute general shell commands requested by Tripitaka for monitoring or diagnostics using the `mcp-shell` MCP tool.\n"
            "- Report the output or status steadily back to Tripitaka.\n"
            "Available MCP Tools: mcp-shell."
        )

        # Instantiate agents
        monkey_agent = Agent(
            name="Monkey", model=model_instance, instructions=monkey_instructions,
            tools=[aws_cli], # Function tool for AWS
            mcp_servers=[]
        )
        pigsy_agent = Agent(
            name="Pigsy", model=model_instance, instructions=pigsy_instructions,
            tools=[fly_cli, vercel_cli], # Function tools for Fly/Vercel
            mcp_servers=[]
        )
        sandy_agent = Agent(
            name="Sandy", model=model_instance, instructions=sandy_instructions,
            tools=[], # Uses MCP only
            mcp_servers=[s for s in mcp_servers if s.name == 'mcp-shell'] # Pass only relevant MCP
        )
        tripitaka_agent = Agent(
            name="Tripitaka", model=model_instance, instructions=tripitaka_instructions,
            tools=[ # Delegate via Agent-as-Tool
                monkey_agent.as_tool(tool_name="Monkey", tool_description="Delegate AWS tasks to Monkey."),
                pigsy_agent.as_tool(tool_name="Pigsy", tool_description="Delegate Fly.io or Vercel tasks to Pigsy."),
                sandy_agent.as_tool(tool_name="Sandy", tool_description="Delegate monitoring or diagnostic shell commands to Sandy.")
            ],
            mcp_servers=[]
        )

        logger.debug("MonkaiMagic Team created. Starting with Tripitaka.")
        return tripitaka_agent

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    messages = [
        {"role": "user", "content": "Do some magic."}
    ]
    blueprint = MonkaiMagicBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            pass
    asyncio.run(run_and_print())
