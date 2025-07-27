import asyncio
import logging
import os
import shlex
import sys
from collections.abc import AsyncGenerator
from typing import Any, ClassVar

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from swarm.core.blueprint_base import BlueprintBase

try:
    from agents import Agent, Runner, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
except ImportError as e:
    print(f"ERROR: Import failed in OmniplexBlueprint: {e}. Check dependencies.")
    sys.exit(1)

logger = logging.getLogger(__name__)

amazo_instructions = """Amazo: You are a specialist in executing JavaScript and Node.js related tasks using npx. You will receive tasks that require npx commands. Execute them and return the output."""
rogue_instructions = """Rogue: You are a specialist in Python execution tasks, particularly using uvx (if available) or standard Python. Execute Python scripts or commands and return the output."""
sylar_instructions = """Sylar: You are a general-purpose specialist. You handle tasks that don't fall under npx or Python/uvx, or when specific tools are assigned to you. Execute commands and return results."""
coordinator_instructions = """Omniplex Coordinator: Your role is to analyze user requests and delegate them to the appropriate specialized agent: Amazo (for npx tasks), Rogue (for Python/uvx tasks), or Sylar (for other tasks). Provide clear instructions to the chosen agent. If unsure, ask for clarification. You have tools representing these agents."""

class OmniplexBlueprint(BlueprintBase):
    metadata: ClassVar[dict[str, Any]] = {
            "name": "OmniplexBlueprint",
            "title": "Omniplex MCP Orchestrator",
            "description": "Dynamically delegates tasks to agents (Amazo:npx, Rogue:uvx, Sylar:other) based on the command type of available MCP servers.",
            "version": "1.1.2",
            "author": "Open Swarm Team (Refactored)",
            "tags": ["orchestration", "mcp", "dynamic", "multi-agent"],
        }

    _openai_client_cache: dict[str, AsyncOpenAI] = {}
    _model_instance_cache: dict[str, Model] = {}

    def __init__(self, blueprint_id: str = "omniplex", config_path: str | None = None, **kwargs: Any):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        # self.config is a property that accesses self._config.
        # self._config is set by _load_configuration in BlueprintBase's __init__.
        # If _load_configuration is mocked to do nothing, self._config might be None.
        if self._config: # Check if _config was populated
            self.mcp_server_configs = self._config.get('mcpServers', {})
        else:
            # This case primarily occurs during testing if _load_configuration is fully mocked
            # and doesn't set self._config. The test fixture should handle setting self._config.
            logger.warning(f"OmniplexBlueprint '{self.blueprint_id}': self._config is None after super().__init__(). mcp_server_configs will be empty. This is expected if _load_configuration is mocked in tests.")
            self.mcp_server_configs = {}

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        logger.debug("Dynamically creating agents for OmniplexBlueprint...")

        if self.config is None: # Access via property, which will raise error if _config is still None
            raise RuntimeError("Configuration could not be loaded in create_starting_agent for Omniplex.")

        default_profile_name = self.llm_profile_name
        logger.debug(f"Using LLM profile '{default_profile_name}' for Omniplex agents.")
        model_instance = self._get_model_instance(default_profile_name) # Inherited

        npx_started_servers: list[MCPServer] = []
        uvx_started_servers: list[MCPServer] = []
        other_started_servers: list[MCPServer] = []

        for server_instance in mcp_servers:
            server_name = server_instance.name
            server_config_from_blueprint = self.mcp_server_configs.get(server_name, {})
            command_def = server_config_from_blueprint.get("command", "")
            command_name = ""
            if isinstance(command_def, list) and command_def:
                command_name = os.path.basename(command_def[0]).lower()
            elif isinstance(command_def, str) and command_def:
                 command_name = os.path.basename(shlex.split(command_def)[0]).lower()

            if "npx" in command_name: npx_started_servers.append(server_instance)
            elif "uvx" in command_name: uvx_started_servers.append(server_instance)
            else: other_started_servers.append(server_instance)

        logger.debug(f"Categorized MCPs - NPX: {[s.name for s in npx_started_servers]}, UVX: {[s.name for s in uvx_started_servers]}, Other: {[s.name for s in other_started_servers]}")
        team_tools: list[Tool] = []

        if npx_started_servers:
            logger.info(f"Creating Amazo for npx servers: {[s.name for s in npx_started_servers]}")
            amazo_agent = Agent(name="Amazo", model=model_instance, instructions=amazo_instructions, tools=[], mcp_servers=npx_started_servers)
            team_tools.append(amazo_agent.as_tool(tool_name="Amazo", tool_description="Delegate npx tasks."))
        else: logger.info("No started npx servers for Amazo.")

        if uvx_started_servers:
            logger.info(f"Creating Rogue for uvx servers: {[s.name for s in uvx_started_servers]}")
            rogue_agent = Agent(name="Rogue", model=model_instance, instructions=rogue_instructions, tools=[], mcp_servers=uvx_started_servers)
            team_tools.append(rogue_agent.as_tool(tool_name="Rogue", tool_description="Delegate uvx tasks."))
        else: logger.info("No started uvx servers for Rogue.")

        if other_started_servers:
            logger.info(f"Creating Sylar for other servers: {[s.name for s in other_started_servers]}")
            sylar_agent = Agent(name="Sylar", model=model_instance, instructions=sylar_instructions, tools=[], mcp_servers=other_started_servers)
            team_tools.append(sylar_agent.as_tool(tool_name="Sylar", tool_description="Delegate other MCP tasks."))
        else: logger.info("No other started servers for Sylar.")

        coordinator_agent = Agent(name="OmniplexCoordinator", model=model_instance, instructions=coordinator_instructions, tools=team_tools, mcp_servers=[])
        logger.info(f"Omniplex Coordinator created with tools for: {[t.name for t in team_tools]}")
        return coordinator_agent

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        logger.info("OmniplexBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        mcp_servers_for_run = kwargs.get("mcp_servers_override", [])

        try:
            starting_agent = self.create_starting_agent(mcp_servers=mcp_servers_for_run)

            if 'Runner' not in globals() or not callable(getattr(Runner, 'run', None)):
                raise RuntimeError("agents.Runner is not available or not callable.")

            async for chunk in Runner.run(starting_agent, instruction):
                yield chunk
        except Exception as e:
            logger.error(f"Error during Omniplex run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

if __name__ == "__main__":
    # ... (main example as before) ...
    import asyncio
    import json
    from pathlib import Path
    from unittest.mock import MagicMock

    dummy_omniplex_config = {
        "llm": {"default": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": os.getenv("OPENAI_API_KEY")}},
        "settings": {"default_llm_profile": "default"},
        "mcpServers": {
            "npx_tool_1": {"command": "npx some-npx-tool", "type": "npx"},
            "other_tool_1": {"command": "python some_script.py", "type": "other"}
        }
    }
    temp_omniplex_config_path = Path("./temp_omniplex_config.json")
    with open(temp_omniplex_config_path, "w") as f:
        json.dump(dummy_omniplex_config, f)

    blueprint = OmniplexBlueprint(config_path=str(temp_omniplex_config_path))

    mock_npx_server = MagicMock(spec=MCPServer); mock_npx_server.name = "npx_tool_1"
    mock_other_server = MagicMock(spec=MCPServer); mock_other_server.name = "other_tool_1"
    example_started_mcps = [mock_npx_server, mock_other_server]

    messages = [{"role": "user", "content": "Use an npx tool to do something."}]

    async def run_and_print():
        async for response in blueprint.run(messages, mcp_servers_override=example_started_mcps):
            print(json.dumps(response, indent=2))

    asyncio.run(run_and_print())
    if temp_omniplex_config_path.exists():
        temp_omniplex_config_path.unlink()
