"""
Utilities for MCP server interactions in the Swarm framework.
Handles discovery and merging of tools and resources from MCP servers.
"""

import logging
from typing import List, Dict, Any, Optional, cast
import asyncio # Needed for async operations

# Import necessary types from the core swarm types
from swarm.types import Agent, AgentFunction
# Import the MCPToolProvider which handles communication with MCP servers
from .mcp_tool_provider import MCPToolProvider

# Configure module-level logging
logger = logging.getLogger(__name__)
# Ensure logger level is set appropriately (e.g., DEBUG for development)
# logger.setLevel(logging.DEBUG) # Uncomment for verbose logging
# Add handler if not already configured by root logger setup
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Dictionary to manage locks for concurrent discovery per agent (optional)
# _discovery_locks: Dict[str, asyncio.Lock] = {}

async def discover_and_merge_agent_tools(agent: Agent, config: Dict[str, Any], debug: bool = False) -> List[AgentFunction]:
    """
    Discover tools from MCP servers listed in the agent's config and merge
    them with the agent's statically defined functions.

    Handles deduplication of discovered tools based on name.

    Args:
        agent: The agent instance for which to discover tools.
        config: The main Swarm configuration dictionary containing MCP server details.
        debug: If True, enable detailed debugging logs.

    Returns:
        List[AgentFunction]: A combined list containing the agent's static functions
                             and unique tools discovered from its associated MCP servers.
                             Returns the agent's static functions if no MCP servers are defined.
                             Returns an empty list if the agent is None.
    """
    if not agent:
        logger.error("Cannot discover tools: Agent object is None.")
        return []
    # Use agent's name for logging clarity
    agent_name = getattr(agent, "name", "UnnamedAgent")

    logger.debug(f"Starting tool discovery for agent '{agent_name}'.")
    # Get the list of MCP servers associated with the agent
    mcp_server_names = getattr(agent, "mcp_servers", [])

    # Retrieve the agent's statically defined functions
    static_functions = getattr(agent, "functions", []) or []
    if not isinstance(static_functions, list):
         logger.warning(f"Agent '{agent_name}' functions attribute is not a list ({type(static_functions)}). Treating as empty.")
         static_functions = []

    # If no MCP servers are listed for the agent, return only static functions
    if not mcp_server_names:
        func_names = [getattr(f, 'name', getattr(f, '__name__', '<unknown>')) for f in static_functions]
        logger.debug(f"Agent '{agent_name}' has no MCP servers listed. Returning {len(static_functions)} static functions: {func_names}")
        return static_functions

    # List to hold tools discovered from all MCP servers
    all_discovered_tools: List[AgentFunction] = []
    # Set to keep track of discovered tool names for deduplication
    discovered_tool_names = set()

    # Iterate through each MCP server listed for the agent
    for server_name in mcp_server_names:
        if not isinstance(server_name, str):
            logger.warning(f"Invalid MCP server name type for agent '{agent_name}': {type(server_name)}. Skipping.")
            continue

        logger.debug(f"Discovering tools from MCP server '{server_name}' for agent '{agent_name}'.")
        # Get the configuration for the specific MCP server from the main config
        server_config = config.get("mcpServers", {}).get(server_name)
        if not server_config:
            logger.warning(f"MCP server '{server_name}' configuration not found in main config for agent '{agent_name}'. Skipping.")
            continue

        try:
            # Get an instance of the MCPToolProvider for this server
            # Timeout can be adjusted based on expected MCP response time
            provider = MCPToolProvider.get_instance(server_name, server_config, timeout=15, debug=debug)
            # Call the provider to discover tools (this interacts with the MCP server)
            discovered_tools_from_server = await provider.discover_tools(agent)

            # Validate the response from the provider
            if not isinstance(discovered_tools_from_server, list):
                logger.warning(f"Invalid tools format received from MCP server '{server_name}' for agent '{agent_name}': Expected list, got {type(discovered_tools_from_server)}. Skipping.")
                continue

            server_tool_count = 0
            for tool in discovered_tools_from_server:
                 # Attempt to get tool name for deduplication and logging
                 tool_name = getattr(tool, 'name', None) # Assuming tool objects have a 'name' attribute
                 if not tool_name:
                      logger.warning(f"Discovered tool from '{server_name}' is missing a 'name'. Skipping.")
                      continue

                 # Deduplication: Add tool only if its name hasn't been seen before
                 if tool_name not in discovered_tool_names:
                     # Ensure 'requires_approval' attribute exists (defaulting to True if missing)
                     if not hasattr(tool, "requires_approval"):
                         logger.debug(f"Tool '{tool_name}' from '{server_name}' missing 'requires_approval', defaulting to True.")
                         try:
                              setattr(tool, "requires_approval", True)
                         except AttributeError:
                              logger.warning(f"Could not set 'requires_approval' on tool '{tool_name}'.")

                     all_discovered_tools.append(tool)
                     discovered_tool_names.add(tool_name)
                     server_tool_count += 1
                 else:
                      logger.debug(f"Tool '{tool_name}' from '{server_name}' is a duplicate. Skipping.")

            tool_names_log = [getattr(t, 'name', '<noname>') for t in discovered_tools_from_server]
            logger.debug(f"Discovered {server_tool_count} unique tools from '{server_name}': {tool_names_log}")

        except Exception as e:
            # Log errors during discovery for a specific server but continue with others
            logger.error(f"Failed to discover tools from MCP server '{server_name}' for agent '{agent_name}': {e}", exc_info=debug) # Show traceback if debug

    # Combine static functions with the unique discovered tools
    # Static functions take precedence if names conflict (though deduplication above is based on discovered names)
    final_functions = static_functions + all_discovered_tools

    # Log final combined list details if debugging
    if debug:
        static_names = [getattr(f, 'name', getattr(f, '__name__', '<unknown>')) for f in static_functions]
        discovered_names = list(discovered_tool_names) # Names of unique discovered tools
        combined_names = [getattr(f, 'name', getattr(f, '__name__', '<unknown>')) for f in final_functions]
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Static functions: {static_names}")
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Unique discovered tools: {discovered_names}")
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Final combined functions: {combined_names}")

    logger.debug(f"Agent '{agent_name}' total functions/tools after merge: {len(final_functions)} (Static: {len(static_functions)}, Discovered: {len(all_discovered_tools)})")
    return final_functions


async def discover_and_merge_agent_resources(agent: Agent, config: Dict[str, Any], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Discover resources from MCP servers listed in the agent's config and merge
    them with the agent's statically defined resources.

    Handles deduplication of discovered resources based on their 'uri'.

    Args:
        agent: The agent instance for which to discover resources.
        config: The main Swarm configuration dictionary containing MCP server details.
        debug: If True, enable detailed debugging logs.

    Returns:
        List[Dict[str, Any]]: A combined list containing the agent's static resources
                              and unique resources discovered from its associated MCP servers.
                              Returns the agent's static resources if no MCP servers are defined.
                              Returns an empty list if the agent is None.
    """
    if not agent:
        logger.error("Cannot discover resources: Agent object is None.")
        return []
    agent_name = getattr(agent, "name", "UnnamedAgent")

    logger.debug(f"Starting resource discovery for agent '{agent_name}'.")
    mcp_server_names = getattr(agent, "mcp_servers", [])

    # Get static resources, ensure it's a list
    static_resources = getattr(agent, "resources", []) or []
    if not isinstance(static_resources, list):
         logger.warning(f"Agent '{agent_name}' resources attribute is not a list ({type(static_resources)}). Treating as empty.")
         static_resources = []
    # Ensure static resources are dicts (basic check)
    static_resources = [r for r in static_resources if isinstance(r, dict)]

    if not mcp_server_names:
        res_names = [r.get('name', '<unnamed>') for r in static_resources]
        logger.debug(f"Agent '{agent_name}' has no MCP servers listed. Returning {len(static_resources)} static resources: {res_names}")
        return static_resources

    # List to hold resources discovered from all MCP servers
    all_discovered_resources: List[Dict[str, Any]] = []

    # Iterate through each MCP server listed for the agent
    for server_name in mcp_server_names:
        if not isinstance(server_name, str):
            logger.warning(f"Invalid MCP server name type for agent '{agent_name}': {type(server_name)}. Skipping.")
            continue

        logger.debug(f"Discovering resources from MCP server '{server_name}' for agent '{agent_name}'.")
        server_config = config.get("mcpServers", {}).get(server_name)
        if not server_config:
            logger.warning(f"MCP server '{server_name}' configuration not found for agent '{agent_name}'. Skipping.")
            continue

        try:
            provider = MCPToolProvider.get_instance(server_name, server_config, timeout=15, debug=debug)
            # Fetch resources using the provider's client
            # Assuming provider.client has a method like list_resources() that returns {'resources': [...]}
            resources_response = await provider.client.list_resources()

            # Validate the structure of the response
            if not isinstance(resources_response, dict) or "resources" not in resources_response:
                logger.warning(f"Invalid resources response format from MCP server '{server_name}' for agent '{agent_name}'. Expected dict with 'resources' key, got: {type(resources_response)}")
                continue

            resources_from_server = resources_response["resources"]
            if not isinstance(resources_from_server, list):
                logger.warning(f"Invalid 'resources' format in response from '{server_name}': Expected list, got {type(resources_from_server)}.")
                continue

            # Filter for valid resource dictionaries (must be dict and have 'uri')
            valid_resources = [res for res in resources_from_server if isinstance(res, dict) and 'uri' in res]
            invalid_count = len(resources_from_server) - len(valid_resources)
            if invalid_count > 0:
                 logger.warning(f"Filtered out {invalid_count} invalid resource entries from '{server_name}'.")

            all_discovered_resources.extend(valid_resources)
            res_names_log = [r.get('name', '<unnamed>') for r in valid_resources]
            logger.debug(f"Discovered {len(valid_resources)} valid resources from '{server_name}': {res_names_log}")

        except AttributeError:
             logger.error(f"MCPToolProvider client for '{server_name}' does not have a 'list_resources' method.", exc_info=debug)
        except Exception as e:
            logger.error(f"Failed to discover resources from MCP server '{server_name}' for agent '{agent_name}': {e}", exc_info=debug)

    # Deduplicate discovered resources based on 'uri'
    # Use a dictionary to keep only the first occurrence of each URI
    unique_discovered_resources_map: Dict[str, Dict[str, Any]] = {}
    for resource in all_discovered_resources:
        uri = resource.get('uri') # URI is expected from validation above
        if uri not in unique_discovered_resources_map:
            unique_discovered_resources_map[uri] = resource

    unique_discovered_resources_list = list(unique_discovered_resources_map.values())

    # Combine static resources with unique discovered resources
    # Create a map of static resource URIs to prevent duplicates if they also exist in discovered
    static_resource_uris = {res.get('uri') for res in static_resources if res.get('uri')}
    final_resources = static_resources + [
        res for res in unique_discovered_resources_list if res.get('uri') not in static_resource_uris
    ]

    if debug:
        static_names = [r.get('name', '<unnamed>') for r in static_resources]
        discovered_names = [r.get('name', '<unnamed>') for r in all_discovered_resources] # Before dedupe
        unique_discovered_names = [r.get('name', '<unnamed>') for r in unique_discovered_resources_list] # After dedupe
        combined_names = [r.get('name', '<unnamed>') for r in final_resources]
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Static resources: {static_names}")
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Discovered resources (before URI dedupe): {discovered_names}")
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Unique discovered resources (after URI dedupe): {unique_discovered_names}")
        logger.debug(f"[DEBUG] Agent '{agent_name}' - Final combined resources: {combined_names}")

    logger.debug(f"Agent '{agent_name}' total resources after merge: {len(final_resources)} (Static: {len(static_resources)}, Unique Discovered: {len(unique_discovered_resources_list)})")
    return final_resources
