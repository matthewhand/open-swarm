from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
# We need MCPServerConfig
from swarm.core.mcp_server_config import MCPServerConfig

class AgentConfig(BaseModel):
    """
    Configuration for an individual agent within a blueprint.
    """
    name: str = Field(..., description="Unique name of the agent.")
    description: Optional[str] = Field(None, description="Description of the agent's role or purpose.")
    instructions: str = Field(..., description="System prompt or instructions for the agent.")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="List of tool schemas available to the agent.")
    model_profile: str = Field("default", description="LLM profile to use for this agent.")
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list, description="List of MCP server configurations relevant to this agent.")

    model_config = ConfigDict(extra='allow')
