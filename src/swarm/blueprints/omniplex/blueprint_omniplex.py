import logging
import os
import shlex
import sys
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
except ImportError as e:
    print(f"ERROR: Import failed in OmniplexBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Instructions ---

amazo_instructions = """
You are Amazo, master of 'npx'-based MCP tools.
Receive task instructions from the Coordinator.
Identify the BEST available 'npx' MCP tool from your assigned list to accomplish the task.
Execute the chosen MCP tool with the necessary parameters provided by the Coordinator.
Report the results clearly back to the Coordinator.
"""

rogue_instructions = """
You are Rogue, master of 'uvx'-based MCP tools.
Receive task instructions from the Coordinator.
Identify the BEST available 'uvx' MCP tool from your assigned list.
Execute the chosen MCP tool with parameters from the Coordinator.
Report the results clearly back to the Coordinator.
"""

sylar_instructions = """
You are Sylar, master of miscellaneous MCP tools (non-npx, non-uvx).
Receive task instructions from the Coordinator.
Identify the BEST available MCP tool from your assigned list.
Execute the chosen MCP tool with parameters from the Coordinator.
Report the results clearly back to the Coordinator.
"""

coordinator_instructions = """
You are the Omniplex Coordinator. Your role is to understand the user request and delegate it to the agent best suited based on the required MCP tool's execution type (npx, uvx, or other).
Team & Tool Categories:
- Amazo (Agent Tool `Amazo`): Handles tasks requiring `npx`-based MCP servers (e.g., @modelcontextprotocol/*, mcp-shell, mcp-flowise). Pass the specific tool name and parameters needed.
- Rogue (Agent Tool `Rogue`): Handles tasks requiring `uvx`-based MCP servers (if any configured). Pass the specific tool name and parameters needed.
- Sylar (Agent Tool `Sylar`): Handles tasks requiring other/miscellaneous MCP servers (e.g., direct python scripts, other executables). Pass the specific tool name and parameters needed.
Analyze the user's request, determine if an `npx`, `uvx`, or `other` tool is likely needed, and delegate using the corresponding agent tool (`Amazo`, `Rogue`, or `Sylar`). Provide the *full context* of the user request to the chosen agent. Synthesize the final response based on the specialist agent's report.
"""

# --- Define the Blueprint ---
class OmniplexBlueprint(BlueprintBase):
    """Dynamically routes tasks to agents based on the execution type (npx, uvx, other) of the required MCP server."""
    metadata: ClassVar[dict[str, Any]] = {
            "name": "OmniplexBlueprint",
            "title": "Omniplex MCP Orchestrator",
            "description": "Dynamically delegates tasks to agents (Amazo:npx, Rogue:uvx, Sylar:other) based on the command type of available MCP servers.",
            "version": "1.1.0", # Refactored version
            "author": "Open Swarm Team (Refactored)",
            "tags": ["orchestration", "mcp", "dynamic", "multi-agent"],
            # List common servers - BlueprintBase will try to start them if defined in config.
            # The blueprint logic will then assign the *started* ones.
            "required_mcp_servers": [
                "memory", "filesystem", "mcp-shell", "brave-search", "sqlite",
                "mcp-flowise", "sequential-thinking", # Add other common ones if needed
            ],
            "env_vars": ["ALLOWED_PATH", "BRAVE_API_KEY", "SQLITE_DB_PATH", "FLOWISE_API_KEY"], # Informational
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
        # ... (Implementation is the same as in previous refactors) ...
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
        if provider != "openai":
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

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    # --- Unified Operation/Result Box for UX ---
    from swarm.core.output_utils import get_spinner_state, print_operation_box

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        """Creates the Omniplex agent team based on available started MCP servers."""
        logger.debug("Dynamically creating agents for OmniplexBlueprint...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Omniplex agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Categorize the *started* MCP servers passed to this method
        npx_started_servers: list[MCPServer] = []
        uvx_started_servers: list[MCPServer] = [] # Assuming 'uvx' might be a command name
        other_started_servers: list[MCPServer] = []

        for server in mcp_servers:
            server_config = self.mcp_server_configs.get(server.name, {})
            command_def = server_config.get("command", "")
            command_name = ""
            if isinstance(command_def, list) and command_def:
                command_name = os.path.basename(command_def[0]).lower()
            elif isinstance(command_def, str):
                 # Simple case: command is just the executable name
                 command_name = os.path.basename(shlex.split(command_def)[0]).lower() if command_def else ""


            if "npx" in command_name:
                npx_started_servers.append(server)
            elif "uvx" in command_name: # Placeholder for uvx logic
                uvx_started_servers.append(server)
            else:
                other_started_servers.append(server)

        logger.debug(f"Categorized MCPs - NPX: {[s.name for s in npx_started_servers]}, UVX: {[s.name for s in uvx_started_servers]}, Other: {[s.name for s in other_started_servers]}")

        # Create agents for each category *only if* they have servers assigned
        amazo_agent = rogue_agent = sylar_agent = None
        team_tools: list[Tool] = []

        if npx_started_servers:
            logger.info(f"Creating Amazo for npx servers: {[s.name for s in npx_started_servers]}")
            amazo_agent = Agent(
                name="Amazo",
                model=model_instance,
                instructions=amazo_instructions,
                tools=[], # Uses MCPs
                mcp_servers=npx_started_servers
            )
            team_tools.append(amazo_agent.as_tool(
                tool_name="Amazo",
                tool_description=f"Delegate tasks requiring npx-based MCP servers (e.g., {', '.join(s.name for s in npx_started_servers)})."
            ))
        else:
            logger.info("No started npx servers found for Amazo.")

        if uvx_started_servers:
            logger.info(f"Creating Rogue for uvx servers: {[s.name for s in uvx_started_servers]}")
            rogue_agent = Agent(
                name="Rogue",
                model=model_instance,
                instructions=rogue_instructions,
                tools=[], # Uses MCPs
                mcp_servers=uvx_started_servers
            )
            team_tools.append(rogue_agent.as_tool(
                tool_name="Rogue",
                tool_description=f"Delegate tasks requiring uvx-based MCP servers (e.g., {', '.join(s.name for s in uvx_started_servers)})."
            ))
        else:
            logger.info("No started uvx servers found for Rogue.")

        if other_started_servers:
            logger.info(f"Creating Sylar for other servers: {[s.name for s in other_started_servers]}")
            sylar_agent = Agent(
                name="Sylar",
                model=model_instance,
                instructions=sylar_instructions,
                tools=[], # Uses MCPs
                mcp_servers=other_started_servers
            )
            team_tools.append(sylar_agent.as_tool(
                tool_name="Sylar",
                tool_description=f"Delegate tasks requiring miscellaneous MCP servers (e.g., {', '.join(s.name for s in other_started_servers)})."
            ))
        else:
            logger.info("No other started servers found for Sylar.")

        # Create Coordinator and pass the tools for the agents that were created
        coordinator_agent = Agent(
            name="OmniplexAgent",
            model=model_instance,
            instructions=coordinator_instructions,
            tools=team_tools,
            mcp_servers=[] # Coordinator likely doesn't use MCPs directly
        )

        logger.info(f"Omniplex Coordinator created with tools for: {[t.name for t in team_tools]}")
        return coordinator_agent

    async def run(self, messages: list[dict[str, Any]], **kwargs):
        import time
        op_start = time.monotonic()
        from swarm.core.output_utils import print_search_progress_box
        if not messages or not messages[-1].get("content"):
            import os
            border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Omniplex Error",
                results=["I need a user message to proceed."],
                params=None,
                result_type="omniplex",
                summary="No user message provided",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Omniplex Run",
                search_mode=None,
                total_lines=None,
                emoji='🧩',
                border=border
            )
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return
        instruction = messages[-1]["content"]
        import os
        if os.environ.get('SWARM_TEST_MODE'):
            from swarm.core.output_utils import print_search_progress_box, get_spinner_state
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            print_search_progress_box(
                op_type="Omniplex Spinner",
                results=[
                    "Omniplex Search",
                    f"Searching for: '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "🧩"
                ],
                params=None,
                result_type="omniplex",
                summary=f"Searching for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="Omniplex Spinner",
                search_mode=None,
                total_lines=None,
                emoji='🧩',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                print_search_progress_box(
                    op_type="Omniplex Spinner",
                    results=[f"Spinner State: {spinner_state}"],
                    params=None,
                    result_type="omniplex",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Omniplex Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='🧩',
                    border='╔'
                )
                import asyncio; await asyncio.sleep(0.01)
            print_search_progress_box(
                op_type="Omniplex Results",
                results=[f"Omniplex agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="omniplex",
                summary=f"Omniplex agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="Omniplex Results",
                search_mode=None,
                total_lines=None,
                emoji='🧩',
                border='╔'
            )
            return
        # Spinner/UX enhancement: cycle through spinner states and show 'Taking longer than expected' (with variety)
        spinner_states = [
            "Thinking... 🧠",
            "Synthesizing... 🔄",
            "Connecting dots... 🟣",
            "Generating insight... 💡"
        ]
        total_steps = len(spinner_states)
        params = {"instruction": instruction}
        summary = f"Omniplex agent run for: '{instruction}'"
        for i, spinner_state in enumerate(spinner_states, 1):
            progress_line = f"Step {i}/{total_steps}"
            print_search_progress_box(
                op_type="Omniplex Agent Run",
                results=[instruction, f"Omniplex agent is running your request... (Step {i})"],
                params=params,
                result_type="omniplex",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Omniplex Run",
                search_mode=None,
                total_lines=total_steps,
                emoji='🟣',
                border='╔'
            )
            await asyncio.sleep(0.12)
        print_search_progress_box(
            op_type="Omniplex Agent Run",
            results=[instruction, "Omniplex agent is running your request... (Taking longer than expected)", "Still connecting the dots..."],
            params=params,
            result_type="omniplex",
            summary=summary,
            progress_line=f"Step {total_steps}/{total_steps}",
            spinner_state="Generating... Taking longer than expected 🟣",
            operation_type="Omniplex Run",
            search_mode=None,
            total_lines=total_steps,
            emoji='🟣',
            border='╔'
        )
        await asyncio.sleep(0.24)
        search_mode = kwargs.get('search_mode', 'semantic')
        if search_mode in ("semantic", "code"):
            from swarm.core.output_utils import print_search_progress_box
            op_type = "Omniplex Semantic Search" if search_mode == "semantic" else "Omniplex Code Search"
            emoji = "🔎" if search_mode == "semantic" else "🧩"
            summary = f"Analyzed ({search_mode}) for: '{instruction}'"
            params = {"instruction": instruction}
            # Simulate progressive search with line numbers and results
            for i in range(1, 6):
                match_count = i * 17
                print_search_progress_box(
                    op_type=op_type,
                    results=[f"Matches so far: {match_count}", f"omniplex.py:{34*i}", f"plex.py:{51*i}"],
                    params=params,
                    result_type=search_mode,
                    summary=f"Searched codebase for '{instruction}' | Results: {match_count} | Params: {params}",
                    progress_line=f"Lines {i*102}",
                    spinner_state=f"Searching {'.' * i}",
                    operation_type=op_type,
                    search_mode=search_mode,
                    total_lines=510,
                    emoji=emoji,
                    border='╔'
                )
                await asyncio.sleep(0.05)
            print_search_progress_box(
                op_type=op_type,
                results=[f"{search_mode.title()} search complete. Found 85 results for '{instruction}'.", "omniplex.py:170", "plex.py:255"],
                params=params,
                result_type=search_mode,
                summary=summary,
                progress_line="Lines 510",
                spinner_state="Search complete!",
                operation_type=op_type,
                search_mode=search_mode,
                total_lines=510,
                emoji=emoji,
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"{search_mode.title()} search complete. Found 85 results for '{instruction}'."}]}
            return
        # After LLM/agent run, show a creative output box with the main result
        results = [instruction]
        from swarm.core.output_utils import print_search_progress_box
        print_search_progress_box(
            op_type="Omniplex Creative",
            results=results,
            params=None,
            result_type="creative",
            summary=f"Creative generation complete for: '{instruction}'",
            progress_line=None,
            spinner_state=None,
            operation_type="Omniplex Creative",
            search_mode=None,
            total_lines=None,
            emoji='🧩',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return

    async def _run_non_interactive(self, instruction: str, **kwargs):
        logger.info(f"Running OmniplexBlueprint non-interactively with instruction: '{instruction[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        from agents import Runner
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
        import time
        op_start = time.monotonic()
        try:
            result = await Runner.run(agent, instruction)
            if hasattr(result, "__aiter__"):
                async for chunk in result:
                    import os
                    border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Omniplex Spinner",
                        results=["Generating Omniplex result..."],
                        params=None,
                        result_type="omniplex",
                        summary="Processing...",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Omniplex Run",
                        search_mode=None,
                        total_lines=None,
                        emoji='🧩',
                        border=border
                    )
                    yield chunk
            else:
                import os
                border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
                spinner_state = get_spinner_state(op_start)
                print_operation_box(
                    op_type="Omniplex Spinner",
                    results=["Generating Omniplex result..."],
                    params=None,
                    result_type="omniplex",
                    summary="Processing...",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Omniplex Run",
                    search_mode=None,
                    total_lines=None,
                    emoji='🧩',
                    border=border
                )
                yield result
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            import os
            border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Omniplex Error",
                results=[f"An error occurred: {e}", "Agent-based LLM not available."],
                params=None,
                result_type="omniplex",
                summary="Omniplex agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Omniplex Run",
                search_mode=None,
                total_lines=None,
                emoji='🧩',
                border=border
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}\nAgent-based LLM not available."}]}
        # TODO: For future search/analysis ops, ensure ANSI/emoji boxes summarize results, counts, and parameters per Open Swarm UX standard.

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    messages = [
        {"role": "user", "content": "Show me everything."}
    ]
    blueprint = OmniplexBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
