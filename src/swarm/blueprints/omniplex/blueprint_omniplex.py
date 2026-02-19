import logging
import os
import shlex
import sys
import time
from typing import Any, ClassVar

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from agents import Agent, Runner, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    from swarm.core.blueprint_base import BlueprintBase
    from swarm.core.blueprint_ux import BlueprintUXImproved
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

    def __init__(self, blueprint_id: str = "omniplex", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id=blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        # Add other attributes as needed for Omniplex
        # ...

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
             try:
                 self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e:
                 raise ValueError(f"Failed to init OpenAI client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
            raise ValueError(f"Failed to init LLM provider: {e}") from e

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

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
            name="OmniplexCoordinator",
            model=model_instance,
            instructions=coordinator_instructions,
            tools=team_tools,
            mcp_servers=[] # Coordinator likely doesn't use MCPs directly
        )

        logger.info(f"Omniplex Coordinator created with tools for: {[t.name for t in team_tools]}")
        return coordinator_agent

    async def run(self, messages: list[dict[str, Any]], **kwargs):
        """Main execution entry point for the Omniplex blueprint."""
        logger.info("OmniplexBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        from agents import Runner
        ux = BlueprintUXImproved(style="serious")
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0  # seconds
        last_spinner_time = start_time
        yielded_spinner = False
        result_chunks = []
        try:
            mcp_servers = kwargs.get('mcp_servers_override', [])
            logger.debug(f"Creating starting agent with {len(mcp_servers)} MCP servers")
            agent = self.create_starting_agent(mcp_servers)
            logger.debug(f"Created agent: {agent.name}")
            runner_gen = Runner.run(agent, instruction)
            logger.debug("Created runner generator")
            logger.debug("Starting while loop to process runner_gen")
            while True:
                now = time.time()
                try:
                    logger.debug("Getting next chunk from runner_gen")
                    chunk = next(runner_gen)
                    logger.debug(f"Got chunk: {type(chunk)}")
                    result_chunks.append(chunk)
                    # If chunk is a final result, wrap and yield
                    if chunk and isinstance(chunk, dict) and "messages" in chunk:
                        content = chunk["messages"][0]["content"] if chunk["messages"] else ""
                        summary = ux.summary("Operation", len(result_chunks), {"instruction": instruction[:40]})
                        box = ux.ansi_emoji_box(
                            title="Omniplex Result",
                            content=content,
                            summary=summary,
                            params={"instruction": instruction[:40]},
                            result_count=len(result_chunks),
                            op_type="run",
                            status="success"
                        )
                        logger.debug("Yielding final result")
                        yield {"messages": [{"role": "assistant", "content": box}]}
                    else:
                        logger.debug("Yielding chunk")
                        yield chunk
                    yielded_spinner = False
                except StopIteration:
                    logger.debug("Runner generator stopped")
                    break
                except Exception as e:
                    logger.debug(f"Exception in runner loop: {e}")
                    if now - last_spinner_time >= spinner_yield_interval:
                        taking_long = (now - start_time > 10)
                        spinner_msg = ux.spinner(spinner_idx, taking_long=taking_long)
                        logger.debug("Yielding spinner")
                        yield {"messages": [{"role": "assistant", "content": spinner_msg}]}
                        spinner_idx += 1
                        last_spinner_time = now
                        yielded_spinner = True
            if not result_chunks and not yielded_spinner:
                yield {"messages": [{"role": "assistant", "content": ux.spinner(0)}]}
        except Exception as e:
            logger.error(f"Error during Omniplex run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

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
