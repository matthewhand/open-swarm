"""
EchoCraft Blueprint: A simple example blueprint for Open Swarm.

This blueprint demonstrates the basic structure and functionality.
It defines a single agent, "Echo", which simply repeats the user's input.
"""
import logging
from typing import List, Dict, Any

# Import necessary components from the 'agents' library and the base class
from agents import Agent
from swarm.extensions.blueprint import BlueprintBase

logger = logging.getLogger(__name__)

# Define the EchoAgent at the module level
class EchoAgent(Agent):
    """A simple agent that echoes the last user message."""
    name: str = "Echo"
    description: str = "Echoes the user's input directly back."

    async def process(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Finds the last user message and returns its content.
        """
        # Find the last message from the user
        last_user_message = next((msg['content'] for msg in reversed(messages) if msg.get('role') == 'user'), None)

        if last_user_message:
            logger.debug(f"EchoAgent received: '{last_user_message}'. Echoing back.")
            return last_user_message
        else:
            logger.warning("EchoAgent couldn't find a user message to echo.")
            return "I didn't receive any input to echo back."

class EchoCraftBlueprint(BlueprintBase):
    """
    EchoCraft Blueprint - Repeats user input.
    """
    # --- Blueprint Metadata ---
    metadata = {
        "name": "EchoCraftBlueprint",
        "title": "EchoCraft",
        "version": "1.1.0", # Increment version if changes are made
        "description": "A very simple blueprint that echoes back whatever the user says.",
        "author": "Open Swarm Contributors",
        "tags": ["Example", "Simple", "Echo", "Test"],
        "required_mcp_servers": [], # No MCP servers needed
        "env_vars": [], # No specific environment variables needed
    }

    # --- Initialization (Inherited) ---
    # Uses the __init__ from BlueprintBase for config loading, logging, etc.

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List) -> Agent:
        """
        Creates and returns the starting agent for this blueprint.
        In this case, it's just the EchoAgent.
        """
        logger.debug("Creating EchoAgent instance.")
        # Instantiate the module-level EchoAgent
        echo_agent = EchoAgent()
        return echo_agent

    # --- Main Execution Logic (Inherited) ---
    # Uses _run_non_interactive from BlueprintBase, which calls create_starting_agent
    # and then uses agents.Runner.run() on the returned agent.

    # --- CLI Entry Point (Inherited) ---
    # Uses main() from BlueprintBase, which parses args and calls _run_non_interactive.

# --- Direct execution example (optional) ---
if __name__ == "__main__":
    # This allows running the blueprint directly using: python blueprint_echocraft.py --instruction "Hello"
    EchoCraftBlueprint.main()

