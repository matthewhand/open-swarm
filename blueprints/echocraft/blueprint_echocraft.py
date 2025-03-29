import logging; import os; import sys; from typing import Dict, Any, List, Optional, ClassVar; from pathlib import Path; import datetime
try: from agents import Agent, function_tool; from agents.mcp import MCPServer; from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e: print(f"ERROR: Import failed: {e}."); sys.exit(1)
logger = logging.getLogger(__name__)
@function_tool
def echo_function(content: str) -> str: logger.info(f"EchoAgent echo: {content}"); return content
class EchoAgent(Agent):
    def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        instructions = "You are EchoAgent. Call `echo_function` with user input."; super().__init__(name="EchoAgent", instructions=instructions, tools=[echo_function], model=kwargs.get('model', 'gpt-4o-mini'), mcp_servers=mcp_servers, **kwargs)
class EchoCraftBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = { # CORRECTED METADATA DEFINITION
            "name": "EchoCraftBlueprint", "title": "EchoCraft Blueprint", "description": "Echoes inputs.",
            "version": "1.1.1", "author": "Swarm", "tags": ["simple", "echo"], "required_mcp_servers": [],
    }
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        logger.debug("Creating EchoAgent."); agent_profile = self.config.get("llm_profile", "default"); logger.info(f"Using profile '{agent_profile}'"); return EchoAgent(model=agent_profile, mcp_servers=mcp_servers)
if __name__ == "__main__": EchoCraftBlueprint.main()
