import logging
import os
import sys
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

SHARED_INSTRUCTIONS = """
You are part of the Grifton family WordPress team. Peter coordinates, Brian manages WordPress.
Roles:
- PeterGrifton (Coordinator): User interface, planning, delegates WP tasks via `BrianGrifton` Agent Tool.
- BrianGrifton (WordPress Manager): Uses `server-wp-mcp` (MCP tool, likely function `wp_call_endpoint`) to manage content based on Peter's requests.
Respond ONLY to the agent who tasked you.
"""

class PeterGriftonAgent(Agent):
    def __init__(self, brian_tool: Tool, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: PeterGrifton, Coordinator. You handle user requests about WordPress.\n"
            "1. Understand the user's goal (create post, edit post, list sites, etc.).\n"
            "2. Delegate the task to Brian using the `BrianGrifton` agent tool.\n"
            "3. Provide ALL necessary details to Brian (content, title, site ID, endpoint details if known, method like GET/POST).\n"
            "4. Relay Brian's response (success, failure, IDs, data) back to the user clearly."
        )
        super().__init__(name="PeterGrifton", instructions=instructions, tools=[brian_tool], **kwargs) # Model from profile

class BrianGriftonAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: BrianGrifton, WordPress Manager. You interact with WordPress sites via the `server-wp-mcp` tool.\n"
            "1. Receive tasks from Peter.\n"
            "2. Determine the correct WordPress REST API endpoint and parameters required (e.g., `site`, `endpoint`, `method`, `params`).\n"
            "3. Call the MCP tool function (likely named `wp_call_endpoint` or similar provided by the MCP server) with the correct JSON arguments.\n"
            "4. Report the outcome (success confirmation, data returned, or error message) precisely back to Peter."
        )
        # MCP server provides the actual tool function
        super().__init__(name="BrianGrifton", instructions=instructions, tools=[], **kwargs)

# --- Define the Blueprint ---
class FamilyTiesBlueprint(BlueprintBase): # Renamed class to match file
    """ Manages WordPress content with a Peter/Brian agent team. """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Family Ties / ChaosCrew WP Manager",
            "description": "Manages WordPress content using Peter (coordinator) and Brian (WP manager via MCP).",
            "version": "1.1.0", # Version bump
            "author": "Open Swarm Team",
            "required_mcp_servers": ["server-wp-mcp"], # Brian needs this
            "cli_name": "famties",
            "env_vars": [] # WP_SITES_PATH needed by MCP server, handled by .env + server config
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for FamilyTiesBlueprint...")
        # Use default profile unless overridden
        brian_agent = BrianGriftonAgent(model=None)
        peter_agent = PeterGriftonAgent(
            model=None,
            brian_tool=brian_agent.as_tool(
                tool_name="BrianGrifton",
                tool_description="Delegate WordPress tasks (create, edit, list sites/posts etc.) to Brian."
            )
        )
        logger.info("Agents created: PeterGrifton, BrianGrifton.")
        return {"PeterGrifton": peter_agent, "BrianGrifton": brian_agent}

if __name__ == "__main__":
    FamilyTiesBlueprint.main()
