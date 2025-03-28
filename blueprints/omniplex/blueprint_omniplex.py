import logging
import os
import sys
import asyncio
from typing import Dict, Any, List

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e: print(f"ERROR: Import failed: {e}"); sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Definitions ---
# Using BlueprintBase which loads swarm_config.json containing mcpServers definitions

class AmazoAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            "You are Amazo, master of 'npx'-based MCP tools.\n"
            "Receive task instructions.\n"
            "Identify the BEST available 'npx' MCP tool from your assigned list to accomplish the task.\n"
            "Execute the chosen MCP tool with the necessary parameters.\n"
            "Report the results."
        )
        # Tools are dynamically added by the library when mcp_servers are assigned
        super().__init__(name="Amazo", instructions=instructions, tools=[], **kwargs)

class RogueAgent(Agent):
     def __init__(self, **kwargs):
        instructions = (
            "You are Rogue, master of 'uvx'-based MCP tools.\n"
            "Receive task instructions.\n"
            "Identify the BEST available 'uvx' MCP tool from your assigned list.\n"
            "Execute the chosen MCP tool.\n"
            "Report the results."
        )
        super().__init__(name="Rogue", instructions=instructions, tools=[], **kwargs)

class SylarAgent(Agent):
     def __init__(self, **kwargs):
        instructions = (
            "You are Sylar, master of miscellaneous MCP tools (non-npx, non-uvx).\n"
            "Receive task instructions.\n"
            "Identify the BEST available MCP tool from your assigned list.\n"
            "Execute the chosen MCP tool.\n"
            "Report the results."
        )
        super().__init__(name="Sylar", instructions=instructions, tools=[], **kwargs)

class OmniplexCoordinator(Agent):
     def __init__(self, team_tools: List[Tool], **kwargs):
         instructions = (
             "You are the Omniplex Coordinator. Your role is to understand the user request and delegate it to the agent best suited based on the required MCP tool's execution type.\n"
             "Team & Tool Categories:\n"
             "- Amazo (Agent Tool `Amazo`): Handles tasks requiring `npx`-based MCP servers.\n"
             "- Rogue (Agent Tool `Rogue`): Handles tasks requiring `uvx`-based MCP servers.\n"
             "- Sylar (Agent Tool `Sylar`): Handles tasks requiring other/miscellaneous MCP servers.\n"
             "Analyze the request, determine if an `npx`, `uvx`, or `other` tool is needed, and delegate using the corresponding agent tool (`Amazo`, `Rogue`, or `Sylar`). Synthesize the final response."
         )
         super().__init__(name="OmniplexCoordinator", instructions=instructions, tools=team_tools, **kwargs)


# --- Define the Blueprint ---
class OmniplexBlueprint(BlueprintBase):
    """ Dynamically loads agents based on MCP server types defined in config. """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Omniplex MCP Orchestrator",
            "description": "Dynamically loads agents (Amazo:npx, Rogue:uvx, Sylar:other) based on available MCP servers.",
            "version": "1.0.0",
            "author": "Open Swarm Team",
            # Required servers will be ALL servers defined in the config, assigned dynamically
            "required_mcp_servers": [], # Let create_agents handle assignment
            "cli_name": "omni",
            "env_vars": [] # Keys handled by .env and server configs
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Dynamically creating agents for OmniplexBlueprint...")
        agents = {}
        mcp_servers = self.swarm_config.get("mcpServers", {})

        npx_servers = [name for name, cfg in mcp_servers.items() if cfg.get("command") == "npx"]
        uvx_servers = [name for name, cfg in mcp_servers.items() if cfg.get("command") == "uvx"]
        other_servers = [name for name in mcp_servers if name not in npx_servers + uvx_servers]

        # Create agents for each category if they have servers
        amazo = Rogue = sylar = None # Initialize to None
        team_tools = []

        if npx_servers:
            logger.info(f"Creating Amazo for npx servers: {npx_servers}")
            amazo = AmazoAgent(model=None) # Use default model profile
            # We assign mcp_servers later in BlueprintBase._run_non_interactive
            # agents["Amazo"] = amazo # Add to dict later with coordinator
            team_tools.append(amazo.as_tool(tool_name="Amazo", tool_description="Delegate tasks requiring npx-based MCP servers (e.g., filesystem, memory, brave-search)."))
        else: logger.info("No npx servers found for Amazo.")

        if uvx_servers:
            logger.info(f"Creating Rogue for uvx servers: {uvx_servers}")
            rogue = RogueAgent(model=None)
            # agents["Rogue"] = rogue
            team_tools.append(rogue.as_tool(tool_name="Rogue", tool_description="Delegate tasks requiring uvx-based MCP servers."))
        else: logger.info("No uvx servers found for Rogue.")

        if other_servers:
            logger.info(f"Creating Sylar for other servers: {other_servers}")
            sylar = SylarAgent(model=None)
            # agents["Sylar"] = sylar
            team_tools.append(sylar.as_tool(tool_name="Sylar", tool_description="Delegate tasks requiring miscellaneous MCP servers."))
        else: logger.info("No other servers found for Sylar.")

        # Create Coordinator and pass the created agent tools
        coordinator = OmniplexCoordinator(model=None, team_tools=team_tools)
        agents["OmniplexCoordinator"] = coordinator # Coordinator is always first

        # Add the specialist agents *after* the coordinator
        if amazo: agents["Amazo"] = amazo
        if rogue: agents["Rogue"] = rogue
        if sylar: agents["Sylar"] = sylar

        # Metadata update - list all servers found as required
        self.metadata["required_mcp_servers"] = list(mcp_servers.keys())
        logger.info(f"Omniplex agents created. Required servers: {self.metadata['required_mcp_servers']}")

        return agents

if __name__ == "__main__":
    OmniplexBlueprint.main()
