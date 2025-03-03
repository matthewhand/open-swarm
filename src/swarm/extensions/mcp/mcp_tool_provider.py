"""
MCPToolProvider Module for Open-Swarm

This module is responsible for discovering tools from MCP (Model Context Protocol) servers
and integrating them into the Open-Swarm framework as `Tool` instances. It handles
communication with MCP servers, constructs callable functions for dynamic tools, and
ensures that these tools are properly validated and integrated into the agent's function list.
"""

import logging
from typing import List, Dict, Any

from swarm.settings import DEBUG
from swarm.types import Tool, Agent
from swarm.extensions.mcp.mcp_client import MCPClient

from .cache_utils import get_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
stream_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(stream_handler)


class MCPToolProvider:
    """
    Singleton MCPToolProvider to discover tools from an MCP server and convert them into `Tool` instances.
    """
    _instances: Dict[str, "MCPToolProvider"] = {}

    @classmethod
    def get_instance(cls, server_name: str, server_config: Dict[str, Any], timeout: int = 15, debug: bool = False) -> "MCPToolProvider":
        """Get or create a singleton instance for the given server name."""
        if server_name not in cls._instances:
            cls._instances[server_name] = cls(server_name, server_config, timeout, debug)
        return cls._instances[server_name]

    def __init__(self, server_name: str, server_config: Dict[str, Any], timeout: int = 15, debug: bool = False):
        """
        Initialize an MCPToolProvider instance with a configurable timeout.

        Args:
            server_name (str): The name of the MCP server.
            server_config (dict): Configuration dictionary for the specific server.
            timeout (int): Timeout in seconds for MCP operations (default 15, overridden by caller if provided).
            debug (bool): If True, MCP server stderr goes to stderr; otherwise, to log file.
        """
        if server_name in self._instances:
            raise ValueError(f"MCPToolProvider for '{server_name}' already initialized. Use get_instance().")
        self.server_name = server_name
        self.client = MCPClient(server_config=server_config, timeout=timeout, debug=debug)
        self.cache = get_cache()
        logger.debug(f"Initialized MCPToolProvider for server '{self.server_name}' with timeout {timeout}s.")

    async def discover_tools(self, agent: Agent) -> List[Tool]:
        """
        Discover tools from the MCP server and return them as a list of `Tool` instances.
        Utilizes Django cache to persist tool metadata if available.

        Args:
            agent (Agent): The agent for which tools are being discovered.

        Returns:
            List[Tool]: A list of discovered `Tool` instances.

        Raises:
            RuntimeError: If tool discovery from the MCP server fails.
        """
        cache_key = f"mcp_tools_{self.server_name}"
        cached_tools = self.cache.get(cache_key)

        if cached_tools:
            logger.debug(f"Retrieved tools for server '{self.server_name}' from cache.")
            tools = []
            for tool_data in cached_tools:
                tool_name = tool_data["name"]
                tool = Tool(
                    name=tool_name,
                    description=tool_data["description"],
                    input_schema=tool_data.get("input_schema", {}),
                    func=self._create_tool_callable(tool_name),
                )
                tools.append(tool)
            return tools

        logger.debug(f"Starting tool discovery from MCP server '{self.server_name}' for agent '{agent.name}'.")
        try:
            tools = await self.client.list_tools()
            logger.debug(f"Discovered tools from MCP server '{self.server_name}': {[tool.name for tool in tools]}")

            # Serialize tools for caching
            serialized_tools = [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': tool.input_schema,
                }
                for tool in tools
            ]

            # Cache the tools for 1 hour (3600 seconds)
            self.cache.set(cache_key, serialized_tools, 3600)
            logger.debug(f"Cached tools for MCP server '{self.server_name}'.")

            return tools

        except Exception as e:
            logger.error(f"Failed to discover tools from MCP server '{self.server_name}': {e}", exc_info=True)
            raise RuntimeError(f"Tool discovery failed for MCP server '{self.server_name}': {e}") from e

    def _create_tool_callable(self, tool_name: str):
        """
        Create a callable function for a dynamically discovered tool.

        Args:
            tool_name (str): The name of the tool.

        Returns:
            Callable: An async callable function for the tool.
        """
        async def dynamic_tool_func(**kwargs) -> Any:
            try:
                logger.info(f"Executing tool '{tool_name}' with arguments: {kwargs}")
                tool_callable = self.client._create_tool_callable(tool_name)
                result = await tool_callable(**kwargs)
                logger.info(f"Tool '{tool_name}' executed successfully: {result}")
                return result
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {e}")
                raise RuntimeError(f"Tool execution failed: {e}") from e

        return dynamic_tool_func
