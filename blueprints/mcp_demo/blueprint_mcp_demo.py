"""
mcp_demo: MCP Demo Blueprint

This blueprint confirms MCP server functionality with a simple demo.
It includes a single agent "Sage" with access to mcp-llms-txt.
"""

import os
import logging
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

class MCPDemoBlueprint(BlueprintBase):
    """
    MCP Demo Blueprint

    This blueprint is designed to confirm MCP server functionality.
    It includes a single agent "Sage" with access to mcp-llms-txt.
    """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "MCP Demo Blueprint",
            "description": "Confirms MCP server functionality with a simple demo.",
            "required_mcp_servers": ["everything", "mcp-llms-txt"],
            "cli_name": "mcpdemo",
            "env_vars": []
        }
    
    def create_agents(self) -> Dict[str, Agent]:
        agents = {}
        agents["Sage"] = Agent(
            name="Sage",
            instructions="You are Sage, a wealth of knowledge. Leverage mcp-llms-txt to provide deep insights and confirm MCP integration.",
            mcp_servers=["mcp-llms-txt"],
            env_vars={}
        )
        self.set_starting_agent(agents["Sage"])
        logger.info("Agent Sage created for MCP Demo Blueprint.")
        agents["Explorer"] = Agent(
            name="Explorer",
            instructions="You are Explorer, skilled in accessing diverse resources. Use 'everything' MCP server to demonstrate comprehensive functionality.",
            mcp_servers=["everything"],
            env_vars={}
        )
        logger.info("Agent Explorer created for MCP Demo Blueprint.")
        def handoff_to_explorer() -> Agent:
            return agents["Explorer"]
        def handoff_to_sage() -> Agent:
            return agents["Sage"]
        agents["Sage"].functions = [handoff_to_explorer]
        agents["Explorer"].functions = [handoff_to_sage]
        return agents

if __name__ == "__main__":
    MCPDemoBlueprint.main()