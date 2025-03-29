import logging
import sys
from typing import List, Dict, Any, Optional, ClassVar

try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer
    # Corrected Import: Remove 'src.' prefix
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in blueprint_echocraft: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tool Definition ---
@function_tool
def simple_echo(text_to_echo: str) -> str:
    """
    Echoes the provided text back to the caller.
    """
    logger.info(f"Echoing text: '{text_to_echo}'")
    return f"Echo: {text_to_echo}"

# --- Agent Definition ---
class EchoAgent(Agent):
    def __init__(self, **kwargs):
        instructions = "You are an Echo Agent. Your only function is to echo back the user's input using the 'simple_echo' tool. Always use the tool, do not just repeat the input in your response text."
        super().__init__(
            name="EchoBot",
            instructions=instructions,
            tools=[simple_echo], # Pass the tool function directly
            **kwargs
        )

# --- Blueprint Definition ---
class EchocraftBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "EchocraftBlueprint",
        "title": "Echocraft - Simple Echo Agent",
        "description": "A basic blueprint demonstrating a single agent with one tool.",
        "version": "1.1.0",
        "author": "Open Swarm Team",
        "tags": ["simple", "echo", "tool", "example"],
        "required_mcp_servers": [], # No MCP needed
    }

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the EchoAgent."""
        logger.info("Creating EchoAgent...")
        # Use the default LLM profile specified in the config or 'default'
        llm_profile_name = self.config.get("llm_profile", "default")
        logger.info(f"Using LLM profile '{llm_profile_name}' for EchoAgent.")
        agent = EchoAgent(model=llm_profile_name)
        logger.info("EchoAgent created.")
        return agent

if __name__ == "__main__":
    EchocraftBlueprint.main()
