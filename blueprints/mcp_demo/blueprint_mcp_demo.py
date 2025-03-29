import logging
import os
import sys
from typing import Dict, List, Optional, Any, ClassVar # Added ClassVar
from pathlib import Path
import datetime # Imported for get_current_time

# --- Use new Agent and Tool types ---
try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer # Import MCPServer for type hint
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed: {e}. Check install and PYTHONPATH.")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Define Tools using @function_tool ---
@function_tool
def get_current_time() -> str:
    """Returns the current system time in ISO format. Use ONLY when asked for the current time."""
    logger.debug("Executing get_current_time tool")
    return datetime.datetime.now().isoformat()

@function_tool
def list_files(path: str = ".") -> List[str]:
    """Lists files and directories in a specified local path. Use ONLY when asked to list files."""
    logger.debug(f"Executing list_files tool with path: {path}")
    try:
        # Simple relative path handling for demo. Needs hardening for security.
        target_path = Path(path)
        # Basic check to prevent escaping parent dirs excessively (very basic security)
        if ".." in target_path.parts and len(target_path.parts) > path.count("..") + 1:
             logger.warning(f"list_files potentially unsafe path rejected: {path}")
             return ["Error: Path potentially unsafe."]
        if not target_path.is_dir():
            logger.error(f"Directory not found for list_files: {target_path}")
            return [f"Error: Directory not found at '{path}'"]
        return os.listdir(target_path)
    except Exception as e:
        logger.error(f"Error in list_files tool at path '{path}': {e}", exc_info=True)
        return [f"Error listing files at '{path}': {e}"]

# --- Define Agents ---
class SageAgent(Agent):
    def __init__(self, explorer_tool: Optional[Tool] = None, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        default_instructions = (
            "You are Sage, an orchestrator agent.\n"
            "AVAILABLE TOOLS:\n"
            "- `get_current_time`: Call this function tool ONLY when explicitly asked for the current time.\n"
            "- `Explorer`: Call this agent tool ONLY when explicitly asked to list files or interact with the filesystem.\n"
            "If the user asks for the time, call `get_current_time`. If the user asks to list files, call `Explorer`. Otherwise, respond directly."
        )
        agent_tools = [get_current_time]
        if explorer_tool: agent_tools.append(explorer_tool)
        super().__init__( name="Sage", instructions=kwargs.get('instructions', default_instructions), tools=agent_tools, mcp_servers=mcp_servers, **kwargs) # Pass mcp_servers

class ExplorerAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs): # Accept mcp_servers
         default_instructions = (
             "You are Explorer, a filesystem agent.\n"
             "AVAILABLE TOOLS:\n"
             "- `list_files`: Call this function tool ONLY when explicitly asked to list files or directory contents.\n"
             "Execute the `list_files` tool with the correct path argument based on the user request."
         )
         super().__init__( name="Explorer", instructions=kwargs.get('instructions', default_instructions), tools=[list_files], mcp_servers=mcp_servers, **kwargs )

     def as_tool( self, tool_name: str | None = None, tool_description: str | None = None, custom_output_extractor: Any = None, ) -> Tool:
         logger.debug(f"Creating tool representation for {self.name}...")
         tool_description = tool_description or "Call this agent tool ONLY for requests involving listing files or interacting with the filesystem."
         return super().as_tool(tool_name=tool_name or "Explorer", tool_description=tool_description, custom_output_extractor=custom_output_extractor)

# --- Define the Blueprint ---
class MCPDemoBlueprint(BlueprintBase):
    # Corrected metadata as a class variable
    metadata: ClassVar[Dict[str, Any]] = {
            "name": "MCPDemoBlueprint", # Added name
            "title": "MCP Demo",
            "description": "Demonstrates multi-agent collaboration with function and MCP tools.",
            "version": "1.4.0", # Incremented version
            "author": "Open Swarm Team",
            "tags": ["mcp", "demo", "multi-agent", "tools"],
            "required_mcp_servers": ["everything_server"], # Use actual required servers
    }

    # Implement create_starting_agent instead of create_agents
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the MCP Demo agent team."""
        logger.info(f"Creating MCP Demo agent team with {len(mcp_servers)} MCP server(s)...")
        default_profile = self.config.get("llm_profile", "default")
        logger.info(f"Using LLM profile '{default_profile}' for MCP Demo agents.")

        # Instantiate agents, passing mcp_servers (though maybe unused by them directly)
        explorer_agent = ExplorerAgent(model=default_profile, mcp_servers=mcp_servers)
        explorer_as_tool = explorer_agent.as_tool()

        # Sage agent orchestrates and needs the Explorer tool and MCP servers
        # (pass mcp_servers to Sage in case its logic evolves to use them directly)
        sage_agent = SageAgent(
            model=default_profile,
            explorer_tool=explorer_as_tool,
            mcp_servers=mcp_servers # Pass MCP servers here
        )

        logger.info("MCP Demo team created. Sage is the starting agent.")
        # Return the orchestrator (Sage) as the starting agent
        return sage_agent

    # Remove old create_agents method if present
    # def create_agents(self) -> Dict[str, Agent]: <-- REMOVED

# --- Main execution block ---
if __name__ == "__main__":
    MCPDemoBlueprint.main()
