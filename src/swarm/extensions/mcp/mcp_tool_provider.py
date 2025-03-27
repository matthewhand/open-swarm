"""
MCPToolProvider Module for Open-Swarm

This module is responsible for discovering tools from MCP (Model Context Protocol) servers
and integrating them into the Open-Swarm framework as `Tool` instances.
"""

import logging
import json
import re # Standard library for regular expressions
from typing import List, Dict, Any

from ...settings import Settings # Use Swarm settings
from ...types import Tool, Agent
from .mcp_client import MCPClient
from .cache_utils import get_cache

# Use Swarm's settings for logging configuration
swarm_settings = Settings()
logger = logging.getLogger(__name__)
logger.setLevel(swarm_settings.log_level.upper())
# Ensure handler is added only if needed
if not logger.handlers and not logging.getLogger('swarm').handlers:
     handler = logging.StreamHandler()
     formatter = logging.Formatter(swarm_settings.log_format.value)
     handler.setFormatter(formatter)
     logger.addHandler(handler)


class MCPToolProvider:
    """
    MCPToolProvider discovers tools from an MCP server and converts them into `Tool` instances.
    Uses caching to avoid repeated discovery.
    """
    _instances: Dict[str, "MCPToolProvider"] = {}

    @classmethod
    def get_instance(cls, server_name: str, server_config: Dict[str, Any], timeout: int = 15, debug: bool = False) -> "MCPToolProvider":
        """Get or create an instance for the given server name."""
        config_key = json.dumps(server_config, sort_keys=True)
        instance_key = f"{server_name}_{config_key}_{timeout}_{debug}"

        if instance_key not in cls._instances:
            logger.debug(f"Creating new MCPToolProvider instance for key: {instance_key}")
            cls._instances[instance_key] = cls(server_name, server_config, timeout, debug)
        else:
             logger.debug(f"Reusing existing MCPToolProvider instance for key: {instance_key}")
        return cls._instances[instance_key]

    def __init__(self, server_name: str, server_config: Dict[str, Any], timeout: int = 15, debug: bool = False):
        """
        Initialize an MCPToolProvider instance. Use get_instance() for shared instances.
        """
        self.server_name = server_name
        effective_debug = debug or swarm_settings.debug
        try:
            self.client = MCPClient(server_config=server_config, timeout=timeout, debug=effective_debug)
        except ImportError as e:
             logger.error(f"Failed to initialize MCPClient for '{server_name}': {e}. MCP features will be unavailable.")
             self.client = None
        except Exception as e:
             logger.error(f"Error initializing MCPClient for '{server_name}': {e}", exc_info=True)
             self.client = None

        self.cache = get_cache()
        logger.debug(f"Initialized MCPToolProvider for server '{self.server_name}' with timeout {timeout}s.")

    async def discover_tools(self, agent: Agent) -> List[Tool]:
        """
        Discover tools from the MCP server using the MCPClient.

        Args:
            agent (Agent): The agent for which tools are being discovered.

        Returns:
            List[Tool]: A list of discovered `Tool` instances with prefixed names.
        """
        if not self.client:
             logger.warning(f"MCPClient for '{self.server_name}' not initialized. Cannot discover tools.")
             return []

        logger.debug(f"Starting tool discovery via MCPClient for server '{self.server_name}'.")
        try:
            tools = await self.client.list_tools()
            logger.debug(f"Discovered {len(tools)} tools from MCP server '{self.server_name}'.")

            separator = "__"
            prefixed_tools = []
            for tool in tools:
                 prefixed_name = f"{self.server_name}{separator}{tool.name}"
                 # Validate prefixed name against OpenAI pattern
                 if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", prefixed_name):
                      logger.warning(f"Generated MCP tool name '{prefixed_name}' might violate OpenAI pattern. Skipping.")
                      continue

                 prefixed_tool = Tool(
                      name=prefixed_name,
                      description=tool.description,
                      input_schema=tool.input_schema,
                      func=tool.func # Callable already targets this client/tool
                 )
                 prefixed_tools.append(prefixed_tool)
                 logger.debug(f"Added prefixed tool: {prefixed_tool.name}")

            return prefixed_tools

        except Exception as e:
            logger.error(f"Failed to discover tools from MCP server '{self.server_name}': {e}", exc_info=True)
            return []

