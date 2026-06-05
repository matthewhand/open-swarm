
from pydantic import BaseModel, ConfigDict, Field


class MCPServerConfig(BaseModel):
    """
    Configuration for an MCP (Multi-Agent Control Plane) server.
    """
    model_config = ConfigDict(extra='allow')

    name: str = Field(..., description="Unique name for the MCP server instance.")
    url: str | None = Field(None, description="URL of the MCP server endpoint, if applicable.")

    # Optional fields that might be part of a server's configuration
    command: str | None = Field(None, description="Command to start the server (e.g., 'python', 'npx').")
    args: list[str] = Field(default_factory=list, description="Arguments for the command.")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the server process.")
    cwd: str | None = Field(None, description="Working directory for the server process.")

