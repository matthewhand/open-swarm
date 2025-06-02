from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class MCPServerConfig(BaseModel):
    """
    Configuration for an MCP (Multi-Agent Control Plane) server.
    """
    name: str = Field(..., description="Unique name for the MCP server instance.")
    url: Optional[str] = Field(None, description="URL of the MCP server endpoint, if applicable.")
    
    # Optional fields that might be part of a server's configuration
    # These are based on common patterns for process/server management.
    command: Optional[str] = Field(None, description="Command to start the server (e.g., 'python', 'npx').")
    args: List[str] = Field(default_factory=list, description="Arguments for the command.")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables for the server process.")
    
    # You might also include fields for authentication, type, etc.
    # type: Optional[str] = Field(None, description="Type of the MCP server (e.g., 'filesystem', 'memory', 'custom').")
    # token_env_var: Optional[str] = Field(None, description="Environment variable name holding an auth token for this server.")

    class Config:
        extra = 'allow' # Allow extra fields if loaded from a more complex config

