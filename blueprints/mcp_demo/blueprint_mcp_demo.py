import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# --- Use new Agent and Tool types ---
from agents import Agent, Tool, function_tool

# --- Use new BlueprintBase ---
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
# No other imports needed for __main__ block

# Setup logger for this specific blueprint module
logger = logging.getLogger(__name__)

# --- Define Tools using @function_tool ---
@function_tool
def get_current_time() -> str:
    """Returns the current system time in ISO format. Use ONLY when asked for the current time."""
    import datetime
    logger.debug("Executing get_current_time tool")
    return datetime.datetime.now().isoformat()

@function_tool
def list_files(path: str = ".") -> List[str]:
    """Lists files and directories found in a specified local directory path on the server. Use ONLY when asked to list files."""
    logger.debug(f"Executing list_files tool with path: {path}")
    try:
        # Use relative path from the blueprint file itself
        base_path = Path(__file__).parent
        target_path = (base_path / path).resolve()
        logger.debug(f"Resolved path for list_files: {target_path}")
        # Ensure target path is within the blueprint directory or a known safe area (security)
        # For demo purposes, we allow relative paths from the blueprint dir.
        # A real implementation might need stricter checks.
        if not str(target_path).startswith(str(base_path)):
             logger.warning(f"list_files attempted to access path outside blueprint directory: {target_path}")
             return ["Error: Access denied."]

        return os.listdir(target_path)
    except FileNotFoundError:
        logger.error(f"Directory not found for list_files: {target_path}")
        return [f"Error: Directory not found at '{path}'"]
    except Exception as e:
        logger.error(f"Error in list_files tool at path '{path}': {e}", exc_info=True)
        return [f"Error listing files at '{path}': {e}"]

# --- Define Agents ---
class SageAgent(Agent):
    def __init__(self, explorer_tool: Optional[Tool] = None, **kwargs):
        default_instructions = (
            "You are Sage, an orchestrator agent.\n"
            "AVAILABLE TOOLS:\n"
            "- `get_current_time`: Call this function tool ONLY when the user explicitly asks for the current time.\n"
            "- `Explorer`: Call this agent tool ONLY when the user explicitly asks to list files or interact with the filesystem (e.g., 'list files in .').\n"
            "If the user asks for the time, call `get_current_time`. If the user asks to list files, call `Explorer`. Otherwise, respond directly."
        )
        agent_tools = [get_current_time]
        if explorer_tool:
            agent_tools.append(explorer_tool)
        super().__init__( name="Sage", instructions=kwargs.get('instructions', default_instructions), tools=agent_tools, model="gpt-4o", **kwargs )

class ExplorerAgent(Agent):
     def __init__(self, **kwargs):
         default_instructions = (
             "You are Explorer, a filesystem agent.\n"
             "AVAILABLE TOOLS:\n"
             "- `list_files`: Call this function tool ONLY when explicitly asked to list files or directory contents. Pass the path specified by the user, or '.' if no path is given.\n"
             "Execute the `list_files` tool with the correct path argument based on the user request."
         )
         super().__init__( name="Explorer", instructions=kwargs.get('instructions', default_instructions), tools=[list_files], model="gpt-4o", **kwargs )

     def as_tool( self, tool_name: str | None = None, tool_description: str | None = None, custom_output_extractor: Any = None, ) -> Tool:
         logger.debug(f"Creating tool representation for {self.name}...")
         tool_description = tool_description or "Call this agent tool ONLY for requests involving listing files or interacting with the filesystem."
         return super().as_tool(tool_name=tool_name or "Explorer", tool_description=tool_description, custom_output_extractor=custom_output_extractor)

class ScholarAgent(Agent):
    def __init__(self, **kwargs):
        default_instructions = "You are Scholar, focused on knowledge retrieval and synthesis."
        super().__init__( name="Scholar", instructions=kwargs.get('instructions', default_instructions), tools=[], model="gpt-4o", **kwargs )

# --- Define the Blueprint ---
class MCPDemoBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "MCP Demo",
            "description": "Demonstrates multi-agent collaboration with function and MCP tools.",
            "version": "1.3.4", # Incremented version
            "author": "Open Swarm Team",
            # Updated required servers: Removed mcp_llms_txt_server
            "required_mcp_servers": ["everything_server"],
            "env_vars": [], # Placeholder for required environment variables
            "max_context_tokens": 8000,
            "max_context_messages": 50,
        }

    def create_agents(self) -> Dict[str, Agent]:
        explorer_agent = ExplorerAgent()
        logger.debug("Agent Explorer created for MCP Demo Blueprint.")
        explorer_as_tool = explorer_agent.as_tool()
        logger.debug("Agent Sage now uses Explorer as a tool.")
        sage_agent = SageAgent(explorer_tool=explorer_as_tool)
        logger.debug("Agent Sage created for MCP Demo Blueprint.")
        scholar_agent = ScholarAgent()
        logger.debug("Agent Scholar created for MCP Demo Blueprint.")
        return { "Sage": sage_agent, "Explorer": explorer_agent, "Scholar": scholar_agent }

# --- Main execution block for direct script run ---
if __name__ == "__main__":
    # The base class main method handles everything via the class itself
    MCPDemoBlueprint.main()
