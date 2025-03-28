"""
mcp_demo: MCP Demo Blueprint

This blueprint confirms MCP server functionality with a simple demo.
It creates a starting agent "Sage" that uses the "Explorer" agent as a tool.
The blueprint super class loads mcp_servers as configuration dictionaries.
In order to bypass the default validation on the mcp_servers field and allow passing dicts,
a custom subclass ConstructAgent of the Agent class is defined with an explicit construct() method.
This approach is based on examples in the openai-agents SDK.
"""

import os
import sys
import logging
from typing import Dict, Any, cast

# Adjust sys.path to include the openai-agents package source directory.
openai_agents_src = os.path.join(os.getcwd(), "openai-agents-python/src")
if openai_agents_src not in sys.path:
    sys.path.insert(0, openai_agents_src)

# Import Agent from the openai-agents SDK.
from agents.agent import Agent  # type: ignore

from agents.mcp.server import MCPServer
from agents.model_settings import ModelSettings

class MCPServerWrapper(MCPServer):
    def __init__(self, name: str, config: dict):
        self._name = name
        self.config = config

    @property
    def name(self) -> str:
        return self._name

    async def connect(self):
        # No connection needed for wrapper.
        pass

    async def cleanup(self):
        # No cleanup necessary.
        pass

    async def list_tools(self) -> list:
        return self.config.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict | None):
        raise NotImplementedError("MCPServerWrapper does not support call_tool.")

class ConstructAgent(Agent):
    class Config:
        extra = "allow"
    
    def __init__(self):
        # No additional initialization needed.
        pass

    @classmethod
    def construct(cls, **data) -> "ConstructAgent":
        data.pop("model_settings", None)
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        obj.input_guardrails = []
        obj.output_guardrails = []  # Added to ensure output_guardrails exists.
        obj.handoffs = []
        obj.__init__()
        if getattr(obj, "model_settings", None) is None:
            object.__setattr__(obj, "model_settings", ModelSettings())
        return obj

# Import MCPServerStdio from the openai-agents package.
from agents.mcp.server import MCPServerStdio  # type: ignore

from swarm.extensions.blueprint import BlueprintBase

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    sh = logging.StreamHandler()
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    sh.setFormatter(fmt)
    logger.addHandler(sh)

class MCPDemoBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Metadata used by this blueprint to load mcp_servers configuration.
        The keys in 'required_mcp_servers' correspond to entries in the configuration.
        """
        return {
            "title": "MCP Demo Blueprint",
            "description": "Confirms MCP server functionality with a simple demo.",
            "required_mcp_servers": ["mcp_llms_txt_server", "everything_server"],
            "cli_name": "mcpdemo",
            "env_vars": []
        }
    
    def create_agents(self) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}
        try:
            mcp_llms_txt_config = self.mcp_servers["mcp_llms_txt_server"]
        except KeyError:
            raise KeyError("Expected 'mcp_llms_txt_server' config not found in mcp_servers.")
        if isinstance(mcp_llms_txt_config, dict):
            mcp_llms_txt_config = MCPServerWrapper("mcp_llms_txt_server", mcp_llms_txt_config)
        
        try:
            everything_config = self.mcp_servers["everything_server"]
        except KeyError:
            raise KeyError("Expected 'everything_server' config not found in mcp_servers.")
        if isinstance(everything_config, dict):
            everything_config = MCPServerWrapper("everything_server", everything_config)
        
        agents["Sage"] = ConstructAgent.construct(
            name="Sage",
            instructions=(
                "You are Sage, a wealth of knowledge. Leverage the mcp_llms_txt_server configuration "
                "to provide deep insights, and use the Explorer tool when additional perspective is needed."
            ),
            mcp_servers=[mcp_llms_txt_config],
            env_vars={},
            model_settings=ModelSettings()
        )
        self.set_starting_agent(agents["Sage"])
        logger.info("Agent Sage created for MCP Demo Blueprint.")
        
        agents["Explorer"] = ConstructAgent.construct(
            name="Explorer",
            instructions=(
                "You are Explorer, skilled in accessing diverse resources. Use the everything_server configuration "
                "to demonstrate comprehensive functionality."
            ),
            mcp_servers=[everything_config],
            env_vars={}
        )
        logger.info("Agent Explorer created for MCP Demo Blueprint.")
        
        explorer_tool = cast(ConstructAgent, agents["Explorer"]).as_tool(
            tool_name="Explorer",
            tool_description="Delegates queries to the Explorer agent for additional insights."
        )
        setattr(agents["Sage"], "tools", [explorer_tool])
        logger.info("Agent Sage now uses Explorer as a tool.")
        
        return agents

if __name__ == "__main__":
    MCPDemoBlueprint.main()