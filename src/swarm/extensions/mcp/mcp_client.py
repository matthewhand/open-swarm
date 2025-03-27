"""
MCP Client Module

Manages connections and interactions with MCP servers using the MCP Python SDK.
Redirects MCP server stderr to log files unless debug mode is enabled.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Callable
from contextlib import contextmanager
import sys
import json # Added for result parsing

# Attempt to import mcp types carefully
try:
    from mcp import ClientSession, StdioServerParameters # type: ignore
    from mcp.client.stdio import stdio_client # type: ignore
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Define dummy classes if mcp is not installed
    class ClientSession: pass
    class StdioServerParameters: pass
    def stdio_client(*args, **kwargs): raise ImportError("mcp library not installed")

from ...types import Tool # Use Tool from swarm.types
from .cache_utils import get_cache
from ...settings import Settings # Import Swarm settings

# Use Swarm's settings for logging configuration
swarm_settings = Settings()
logger = logging.getLogger(__name__)
logger.setLevel(swarm_settings.log_level.upper()) # Use log level from settings
# Ensure handler is added only if needed, respecting potential global config
if not logger.handlers and not logging.getLogger('swarm').handlers:
     handler = logging.StreamHandler()
     # Use log format from settings
     formatter = logging.Formatter(swarm_settings.log_format.value)
     handler.setFormatter(formatter)
     logger.addHandler(handler)

class MCPClient:
    """
    Manages connections and interactions with MCP servers using the MCP Python SDK.
    """

    def __init__(self, server_config: Dict[str, Any], timeout: int = 15, debug: bool = False):
        """
        Initialize the MCPClient with server configuration.

        Args:
            server_config (dict): Configuration dictionary for the MCP server.
            timeout (int): Timeout for operations in seconds.
            debug (bool): If True, MCP server stderr goes to console; otherwise, suppressed.
        """
        if not MCP_AVAILABLE:
            raise ImportError("The 'mcp-client' library is required for MCP functionality but is not installed.")

        self.command = server_config.get("command", "npx")
        self.args = server_config.get("args", [])
        self.env = {**os.environ.copy(), **server_config.get("env", {})}
        self.timeout = timeout
        self.debug = debug or swarm_settings.debug # Use instance debug or global debug
        self._tool_cache: Dict[str, Tool] = {}
        self.cache = get_cache()

        # Validate command and args types
        if not isinstance(self.command, str):
             raise TypeError(f"MCP server command must be a string, got {type(self.command)}")
        if not isinstance(self.args, list) or not all(isinstance(a, str) for a in self.args):
             raise TypeError(f"MCP server args must be a list of strings, got {self.args}")


        logger.info(f"Initialized MCPClient with command={self.command}, args={self.args}, debug={self.debug}")

    @contextmanager
    def _redirect_stderr(self):
        """Redirects stderr to /dev/null if not in debug mode."""
        if not self.debug:
            original_stderr = sys.stderr
            devnull = None
            try:
                devnull = open(os.devnull, "w")
                sys.stderr = devnull
                yield
            except Exception:
                 # Restore stderr even if there was an error opening /dev/null or during yield
                 if devnull: devnull.close()
                 sys.stderr = original_stderr
                 raise # Re-raise the exception
            finally:
                if devnull: devnull.close()
                sys.stderr = original_stderr
        else:
            # If debug is True, don't redirect
            yield

    async def list_tools(self) -> List[Tool]:
        """
        Discover tools from the MCP server and cache their schemas.

        Returns:
            List[Tool]: A list of discovered tools with schemas.
        """
        logger.debug(f"Entering list_tools for command={self.command}, args={self.args}")

        # Attempt to retrieve tools from cache
        # Create a more robust cache key
        args_string = json.dumps(self.args, sort_keys=True) # Serialize args consistently
        cache_key = f"mcp_tools_{self.command}_{args_string}"
        cached_tools_data = self.cache.get(cache_key)

        if cached_tools_data:
            logger.debug("Retrieved tools data from cache")
            tools = []
            for tool_data in cached_tools_data:
                tool_name = tool_data["name"]
                # Create Tool instance, ensuring func is a callable wrapper
                tool = Tool(
                    name=tool_name,
                    description=tool_data["description"],
                    input_schema=tool_data.get("input_schema", {"type": "object", "properties": {}}),
                    func=self._create_tool_callable(tool_name), # Use the factory method
                )
                self._tool_cache[tool_name] = tool # Store in instance cache too
                tools.append(tool)
            logger.debug(f"Returning {len(tools)} cached tools")
            return tools

        # If not in cache, discover from server
        server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
        logger.debug("Opening stdio_client connection")
        try:
            async with stdio_client(server_params) as (read, write):
                logger.debug("Opening ClientSession")
                async with ClientSession(read, write) as session:
                    logger.info("Initializing session for tool discovery")
                    await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                    logger.info("Requesting tool list from MCP server...")
                    tools_response = await asyncio.wait_for(session.list_tools(), timeout=self.timeout)
                    logger.debug(f"Tool list received: {tools_response}")

                    if not hasattr(tools_response, 'tools') or not isinstance(tools_response.tools, list):
                        logger.error(f"Invalid tool list response from MCP server: {tools_response}")
                        return []

                    serialized_tools = []
                    tools = []
                    for tool_proto in tools_response.tools:
                         if not hasattr(tool_proto, 'name') or not tool_proto.name:
                              logger.warning(f"Skipping tool with missing name in response: {tool_proto}")
                              continue

                         # Ensure inputSchema exists and is a dict, default if not
                         input_schema = getattr(tool_proto, 'inputSchema', None)
                         if not isinstance(input_schema, dict):
                              input_schema = {"type": "object", "properties": {}}

                         description = getattr(tool_proto, 'description', "") or "" # Ensure description is string

                         serialized_tool_data = {
                              'name': tool_proto.name,
                              'description': description,
                              'input_schema': input_schema,
                         }
                         serialized_tools.append(serialized_tool_data)

                         # Create Tool instance for returning
                         discovered_tool = Tool(
                              name=tool_proto.name,
                              description=description,
                              input_schema=input_schema,
                              func=self._create_tool_callable(tool_proto.name),
                         )
                         self._tool_cache[tool_proto.name] = discovered_tool # Cache instance
                         tools.append(discovered_tool)
                         logger.debug(f"Discovered tool: {tool_proto.name} with schema: {input_schema}")

                    # Cache the serialized data
                    self.cache.set(cache_key, serialized_tools, 3600)
                    logger.debug(f"Cached {len(serialized_tools)} tools.")

                    logger.debug(f"Returning {len(tools)} tools from MCP server")
                    return tools

        except asyncio.TimeoutError:
            logger.error(f"Timeout after {self.timeout}s waiting for tool list")
            raise RuntimeError("Tool list request timed out")
        except Exception as e:
            logger.error(f"Error listing tools: {e}", exc_info=True)
            raise RuntimeError(f"Failed to list tools: {e}") from e

    async def _do_list_resources(self) -> Any:
        """Internal method to list resources with timeout."""
        server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
        logger.debug("Opening stdio_client connection for resources")
        try:
            async with stdio_client(server_params) as (read, write):
                logger.debug("Opening ClientSession for resources")
                async with ClientSession(read, write) as session:
                    with self._redirect_stderr(): # Suppress stderr if not debugging
                        logger.debug("Initializing session before listing resources")
                        await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                        logger.info("Requesting resource list from MCP server...")
                        resources_response = await asyncio.wait_for(session.list_resources(), timeout=self.timeout)
                    logger.debug("Resource list received from MCP server")
                    return resources_response
        except asyncio.TimeoutError:
             logger.error(f"Timeout listing resources after {self.timeout}s")
             raise RuntimeError("Resource list request timed out")
        except Exception as e:
             logger.error(f"Error listing resources: {e}", exc_info=True)
             raise RuntimeError(f"Failed to list resources: {e}") from e

    def _create_tool_callable(self, tool_name: str) -> Callable[..., Any]:
        """
        Dynamically create an async callable function for the specified tool.
        This callable will establish a connection and execute the tool on demand.
        """
        async def dynamic_tool_func(**kwargs) -> Any:
            logger.debug(f"Creating tool callable for '{tool_name}'")
            server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize session first
                        logger.debug(f"Initializing session for tool '{tool_name}'")
                        await asyncio.wait_for(session.initialize(), timeout=self.timeout)

                        # Validate input if schema is available in instance cache
                        if tool_name in self._tool_cache:
                            tool = self._tool_cache[tool_name]
                            self._validate_input_schema(tool.input_schema, kwargs)
                        else:
                            logger.warning(f"Schema for tool '{tool_name}' not found in cache for validation.")

                        logger.info(f"Calling tool '{tool_name}' with arguments: {kwargs}")
                        # Execute the tool call
                        result_proto = await asyncio.wait_for(session.call_tool(tool_name, kwargs), timeout=self.timeout)

                        # Process result (assuming result_proto has a 'result' attribute)
                        result_data = getattr(result_proto, 'result', None)
                        if result_data is None:
                            logger.warning(f"Tool '{tool_name}' executed but returned no result data.")
                            return None # Or raise error?

                        # Attempt to parse if it looks like JSON, otherwise return as is
                        if isinstance(result_data, str):
                            try:
                                parsed_result = json.loads(result_data)
                                logger.info(f"Tool '{tool_name}' executed successfully (result parsed as JSON).")
                                return parsed_result
                            except json.JSONDecodeError:
                                logger.info(f"Tool '{tool_name}' executed successfully (result returned as string).")
                                return result_data # Return raw string if not JSON
                        else:
                             logger.info(f"Tool '{tool_name}' executed successfully (result type: {type(result_data)}).")
                             return result_data # Return non-string result directly

            except asyncio.TimeoutError:
                logger.error(f"Timeout after {self.timeout}s executing tool '{tool_name}'")
                raise RuntimeError(f"Tool '{tool_name}' execution timed out")
            except Exception as e:
                logger.error(f"Failed to execute tool '{tool_name}': {e}", exc_info=True)
                raise RuntimeError(f"Tool execution failed: {e}") from e

        return dynamic_tool_func

    def _validate_input_schema(self, schema: Dict[str, Any], kwargs: Dict[str, Any]):
        """
        Validate the provided arguments against the input schema.
        """
        # Ensure schema is a dictionary, default to no-op if not
        if not isinstance(schema, dict):
            logger.warning(f"Invalid schema format for validation: {type(schema)}. Skipping.")
            return

        required_params = schema.get("required", [])
        # Ensure required_params is a list
        if not isinstance(required_params, list):
            logger.warning(f"Invalid 'required' list in schema: {type(required_params)}. Skipping requirement check.")
            required_params = []

        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: '{param}'")

        # Optional: Add type validation based on schema['properties'][param]['type']
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, value in kwargs.items():
                 if key in properties:
                      expected_type = properties[key].get("type")
                      # Basic type mapping (add more as needed)
                      type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
                      if expected_type in type_map:
                           if not isinstance(value, type_map[expected_type]):
                                logger.warning(f"Type mismatch for parameter '{key}'. Expected '{expected_type}', got '{type(value).__name__}'. Attempting to proceed.")
                                # Allow proceeding but log warning, or raise ValueError for strict validation

        logger.debug(f"Validated input against schema: {schema} with arguments: {kwargs}")

    async def list_resources(self) -> Any:
        """
        Discover resources from the MCP server using the internal method with enforced timeout.
        """
        return await self._do_list_resources() # Timeout handled in _do_list_resources

    async def get_resource(self, resource_uri: str) -> Any:
        """
        Retrieve a specific resource from the MCP server.

        Args:
            resource_uri (str): The URI of the resource to retrieve.

        Returns:
            Any: The resource retrieval response.
        """
        server_params = StdioServerParameters(command=self.command, args=self.args, env=self.env)
        logger.debug("Opening stdio_client connection for resource retrieval")
        try:
            async with stdio_client(server_params) as (read, write):
                logger.debug("Opening ClientSession for resource retrieval")
                async with ClientSession(read, write) as session:
                    with self._redirect_stderr(): # Suppress stderr if not debugging
                        logger.debug(f"Initializing session for resource retrieval of {resource_uri}")
                        await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                        logger.info(f"Retrieving resource '{resource_uri}' from MCP server")
                        response = await asyncio.wait_for(session.read_resource(resource_uri), timeout=self.timeout)
                    logger.info(f"Resource '{resource_uri}' retrieved successfully")
                    # Process response if needed (e.g., getattr(response, 'content', None))
                    return response
        except asyncio.TimeoutError:
            logger.error(f"Timeout retrieving resource '{resource_uri}' after {self.timeout}s")
            raise RuntimeError(f"Resource '{resource_uri}' retrieval timed out")
        except Exception as e:
            logger.error(f"Failed to retrieve resource '{resource_uri}': {e}", exc_info=True)
            raise RuntimeError(f"Resource retrieval failed: {e}") from e

