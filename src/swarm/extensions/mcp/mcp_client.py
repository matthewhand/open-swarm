"""
MCP Client Module

Manages connections and interactions with MCP servers using the MCP Python SDK.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from swarm.types import Tool

from .cache_utils import get_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MCPClient:
    """
    Manages connections and interactions with MCP servers using the MCP Python SDK.
    """

    def __init__(self, server_config: Dict[str, Any], timeout: int = 15):
        """
        Initialize the MCPClient with server configuration.

        Args:
            server_config (dict): Configuration dictionary for the MCP server.
            timeout (int): Timeout for operations in seconds.
        """
        self.command = server_config.get("command", "npx")
        self.args = server_config.get("args", [])
        self.env = {**os.environ.copy(), **server_config.get("env", {})}
        self.timeout = timeout
        self._tool_cache: Dict[str, Tool] = {}

        # Initialize cache using the helper
        self.cache = get_cache()

        logger.info(f"Initialized MCPClient with command={self.command}, args={self.args}")

    async def list_tools(self) -> List[Tool]:
        """
        Discover tools from the MCP server and cache their schemas.

        Returns:
            List[Tool]: A list of discovered tools with schemas.
        """
        # Attempt to retrieve tools from cache
        args_string = "_".join(self.args)
        cache_key = f"mcp_tools_{self.command}_{args_string}"
        cached_tools = self.cache.get(cache_key)

        if cached_tools:
            logger.debug("Retrieved tools from cache")
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

        server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                try:
                    logger.info("Requesting tool list from MCP server...")
                    tools_response = await asyncio.wait_for(session.list_tools(), timeout=self.timeout)

                    serialized_tools = [
                        {
                            'name': tool.name,
                            'description': tool.description,
                            'input_schema': tool.inputSchema,
                        }
                        for tool in tools_response.tools
                    ]
                    
                    self.cache.set(cache_key, serialized_tools, 3600)
                    logger.debug(f"Cached {len(serialized_tools)} tools.")

                    tools = []
                    for tool in tools_response.tools:
                        input_schema = tool.inputSchema or {}
                        cached_tool = Tool(
                            name=tool.name,
                            description=tool.description,
                            input_schema=input_schema,
                            func=self._create_tool_callable(tool.name),
                        )
                        self._tool_cache[tool.name] = cached_tool
                        tools.append(cached_tool)
                        logger.debug(f"Discovered tool: {tool.name} with schema: {input_schema}")

                    return tools

                except Exception as e:
                    logger.error(f"Error listing tools: {e}")
                    raise RuntimeError("Failed to list tools.") from e

    def _create_tool_callable(self, tool_name: str) -> Callable[..., Any]:
        """
        Dynamically create a callable function for the specified tool.
        """
        async def dynamic_tool_func(**kwargs) -> Any:
            server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    try:
                        await session.initialize()
                        if tool_name in self._tool_cache:
                            tool = self._tool_cache[tool_name]
                            self._validate_input_schema(tool.input_schema, kwargs)
                        logger.info(f"Calling tool '{tool_name}' with arguments: {kwargs}")
                        result = await asyncio.wait_for(session.call_tool(tool_name, kwargs), timeout=self.timeout)
                        logger.info(f"Tool '{tool_name}' executed successfully: {result}")
                        return result
                    except Exception as e:
                        logger.error(f"Failed to execute tool '{tool_name}': {e}")
                        raise RuntimeError(f"Tool execution failed: {e}") from e

        dynamic_tool_func.dynamic = True
        return dynamic_tool_func

    def _validate_input_schema(self, schema: Dict[str, Any], kwargs: Dict[str, Any]):
        """
        Validate the provided arguments against the input schema.
        """
        if not schema:
            logger.debug("No input schema available for validation. Skipping.")
            return

        required_params = schema.get("required", [])
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: '{param}'")

        logger.debug(f"Validated input against schema: {schema} with arguments: {kwargs}")
