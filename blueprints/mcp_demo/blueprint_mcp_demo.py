import logging
import sys
import time
from typing import List, Dict, Any, Optional, ClassVar

try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer # Import MCPServer for type hint
    # Corrected Import: Remove 'src.' prefix
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in blueprint_mcp_demo: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


logger = logging.getLogger(__name__)

# --- Tool Definitions ---

@function_tool
def get_current_time() -> str:
    """Returns the current system time."""
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info(f"Tool returning current time: {current_time}")
    return current_time

# --- Agent Definition ---

class MCPSageAgent(Agent):
    def __init__(self, mcp_servers: List[MCPServer], **kwargs):
        instructions = """
You are Sage, an agent that can use capabilities provided by connected MCP servers and local tools.
Available local tools: get_current_time.
Available MCP tools: Provided by connected servers (e.g., filesystem, memory). Use these for tasks involving file access or memory storage.
Analyze the user's request and use the appropriate tool (local or MCP) to fulfill it.
If asked to list tools, list both local and MCP tools. MCP tools are accessed via `call_mcp_tool(server_name="...", tool_name="...", arguments={...})`.
"""
        # Pass the mcp_servers list to the Agent constructor.
        # The Agent base class (from openai-agents) automatically makes MCP tools available.
        super().__init__(
            name="Sage",
            instructions=instructions,
            tools=[get_current_time], # List only local tools here
            mcp_servers=mcp_servers,  # Pass MCP servers here
            **kwargs
        )

# --- Blueprint Definition ---

class MCPDemoBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "MCPDemoBlueprint",
        "title": "MCP Demo Agent (Sage)",
        "description": "Demonstrates an agent using both local tools and tools from MCP servers (e.g., filesystem, memory).",
        "version": "1.1.0",
        "author": "Open Swarm Team",
        "tags": ["mcp", "tools", "filesystem", "memory", "example"],
        # Specify required MCP servers by name (matching keys in swarm_config.json)
        "required_mcp_servers": ["filesystem", "memory"],
    }

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the MCPSageAgent, passing the connected MCP servers."""
        logger.info(f"Creating MCPSageAgent with {len(mcp_servers)} MCP server(s)...")
        # Pass the successfully started MCP servers to the agent instance
        llm_profile_name = self.config.get("llm_profile", "default")
        logger.info(f"Using LLM profile '{llm_profile_name}' for MCPSageAgent.")
        agent = MCPSageAgent(model=llm_profile_name, mcp_servers=mcp_servers)
        logger.info("MCPSageAgent created.")
        return agent

if __name__ == "__main__":
    MCPDemoBlueprint.main()
