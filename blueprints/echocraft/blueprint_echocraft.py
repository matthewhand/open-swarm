import logging
import os
import sys
from typing import Dict, Any

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Use new Agent and Tool types ---
try:
    from agents import Agent, function_tool
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
     print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     sys.exit(1)

# Setup logger for this specific blueprint module
logger = logging.getLogger(__name__)

# --- Define Tools ---
@function_tool
def echo_function(content: str) -> str:
    """
    Simply echoes back the provided text content.
    This is the only tool available. Use it for every user request.
    Args:
        content (str): The user's input text.
    Returns:
        str: The exact same input text.
    """
    logger.info(f"EchoAgent received content: {content}")
    logger.debug("Executing echo_function tool.")
    return content

# --- Define Agent ---
class EchoAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            "You are EchoAgent. Your ONLY function is to echo back the user's input.\n"
            "You MUST call the `echo_function` tool for every request you receive.\n"
            "Pass the user's exact input to the `content` parameter of the `echo_function` tool."
        )
        super().__init__(
            name="EchoAgent",
            instructions=instructions,
            tools=[echo_function], # Provide the echo tool
            model="gpt-4o", # Or use default profile
            # Removed NeMo guardrails config
            # Removed mcp_servers, env_vars (handled by BlueprintBase)
            **kwargs
        )

# --- Define the Blueprint ---
class EchoCraftBlueprint(BlueprintBase):
    """ A blueprint that defines a single agent which echoes user inputs. """

    @property
    def metadata(self) -> Dict[str, Any]:
        """ Metadata for the EchoCraftBlueprint. """
        return {
            "title": "EchoCraft Blueprint",
            "description": "A basic blueprint using openai-agents that echoes user inputs via a tool.",
            "version": "1.0.0",
            "author": "Open Swarm Team",
            "required_mcp_servers": [], # No MCP servers needed
            "cli_name": "echocraft", # Keep cli_name if used elsewhere
            "env_vars": ["OPENAI_API_KEY"], # Depends on LLM profile used
        }

    def create_agents(self) -> Dict[str, Agent]:
        """ Create the EchoAgent. """
        logger.debug("Creating agents for EchoCraftBlueprint.")
        echo_agent = EchoAgent()
        # No need for self.set_starting_agent, BlueprintBase determines it
        return {"EchoAgent": echo_agent}


if __name__ == "__main__":
    EchoCraftBlueprint.main()
