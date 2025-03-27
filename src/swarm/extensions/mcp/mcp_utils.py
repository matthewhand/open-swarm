import os
import json
import httpx
import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
import cachetools.func
import anyio

# Import needed function from config_loader
from ..config.config_loader import get_server_params

# --- FIX: Import FunctionDefinition instead of FunctionProperty ---
from ...types import Agent, ToolDefinition, FunctionDefinition

from .mcp_constants import MCP_SEPARATOR, MCP_DEFAULT_PORT
from ...utils.log_utils import mcp_log_filter
from ...utils.redact import redact_sensitive_data

# Apply the filter to the logger
logger = logging.getLogger(__name__)
logger.addFilter(mcp_log_filter)

# Cache for discovered tools to avoid repeated lookups
@cachetools.func.ttl_cache(maxsize=128, ttl=300)
async def _discover_tools_cached(agent_name: str, server_list_tuple: Tuple[str, ...], config_json_string: str) -> Dict[str, ToolDefinition]:
    """Cached async function to discover tools from MCP servers."""
    logger.debug(f"Cache miss or expired for tool discovery: Agent '{agent_name}', Servers {list(server_list_tuple)}")
    discovered_tools = {}
    try:
        config = json.loads(config_json_string)
        mcp_server_configs = config.get("mcpServers", {})

        async with anyio.create_task_group() as tg:
            for server_name in server_list_tuple:
                if server_name not in mcp_server_configs:
                    logger.warning(f"Configuration for MCP server '{server_name}' not found. Skipping discovery.")
                    continue

                server_params = get_server_params(mcp_server_configs[server_name], server_name)
                if not server_params:
                     logger.error(f"Invalid params for MCP server '{server_name}'. Skipping discovery.")
                     continue

                port = mcp_server_configs[server_name].get("port", MCP_DEFAULT_PORT)
                base_url = f"http://127.0.0.1:{port}"
                tg.start_soon(_discover_single_server, server_name, base_url, discovered_tools)

    except json.JSONDecodeError:
        logger.exception("Error decoding config JSON string in cached discovery.")
        return {}
    except Exception as e:
        logger.exception(f"Error during cached MCP tool discovery for agent '{agent_name}': {e}")
        return {}

    logger.debug(f"Finished MCP tool discovery for agent '{agent_name}'. Found {len(discovered_tools)} tools.")
    return discovered_tools


async def _discover_single_server(server_name: str, base_url: str, discovered_tools: Dict[str, ToolDefinition]):
    """Async helper to discover tools from a single MCP server."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            response = await client.get("/.well-known/openapi.json")
            response.raise_for_status()
            openapi_spec = response.json()
            logger.debug(f"Successfully retrieved OpenAPI spec from {server_name} ({base_url}).")
            server_tools = parse_openapi_for_tools(openapi_spec, server_name)
            logger.info(f"Parsed {len(server_tools)} tools from {server_name}.")
            for tool_name, tool_def in server_tools.items():
                unique_tool_name = f"{server_name}{MCP_SEPARATOR}{tool_name}"
                discovered_tools[unique_tool_name] = tool_def
                logger.debug(f"Discovered tool '{unique_tool_name}' from {server_name}.")
    except httpx.RequestError as e:
        logger.error(f"HTTP error discovering tools from {server_name} ({base_url}): {e}")
    except httpx.HTTPStatusError as e:
         logger.error(f"HTTP status error discovering tools from {server_name}: {e.response.status_code} - {e.response.text}")
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response from {server_name} ({base_url}).")
    except Exception as e:
        logger.exception(f"Unexpected error discovering tools from {server_name} ({base_url}): {e}")


def parse_openapi_for_tools(openapi_spec: Dict[str, Any], server_name: str) -> Dict[str, ToolDefinition]:
    """Parses an OpenAPI spec and returns a dictionary of ToolDefinitions."""
    tools = {}
    paths = openapi_spec.get("paths", {})
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.lower() != "post": continue

            operation_id = operation.get("operationId")
            summary = operation.get("summary")
            description = operation.get("description", summary or "")

            if not operation_id:
                operation_id = f"{path.strip('/').replace('/', '_')}_{method}".lower()
                logger.warning(f"Operation at '{path}' ({method}) missing operationId. Generated: '{operation_id}'.")

            parameters_schema = {"type": "object", "properties": {}, "required": []}
            request_body = operation.get("requestBody")
            if request_body and "content" in request_body:
                 json_schema = request_body["content"].get("application/json", {}).get("schema")
                 if json_schema:
                     if "properties" in json_schema and isinstance(json_schema["properties"], dict):
                        parameters_schema["properties"] = json_schema.get("properties", {})
                        parameters_schema["required"] = json_schema.get("required", [])
                     else:
                         logger.warning(f"Schema for {operation_id} ({server_name}) found but is not a standard object schema with properties. Assuming no parameters.")

            # --- FIX: Use FunctionDefinition ---
            function_def = FunctionDefinition(
                name=operation_id,
                description=description,
                parameters=parameters_schema
            )
            tools[operation_id] = ToolDefinition(type="function", function=function_def)

    return tools


async def discover_tools_for_agent(agent: Agent, config: Dict[str, Any]) -> List[ToolDefinition]:
    """
    Discovers available tools for a given agent, combining static and dynamic (MCP) tools.
    Handles potential errors during MCP discovery gracefully.
    """
    logger.debug(f"Starting tool discovery for agent '{agent.name}'.")
    static_tools_dict: Dict[str, ToolDefinition] = {}
    if hasattr(agent, 'functions') and agent.functions:
        for func in agent.functions:
            if callable(func):
                tool_name = func.__name__
                docstring = func.__doc__ or f"Executes the {tool_name} function."
                params = {"type": "object", "properties": {}} # Placeholder
                # --- FIX: Use FunctionDefinition ---
                static_tools_dict[tool_name] = ToolDefinition(
                    type="function",
                    function=FunctionDefinition(name=tool_name, description=docstring.strip(), parameters=params)
                )
    logger.debug(f"[DEBUG] Agent '{agent.name}' - Static functions definitions created: {len(static_tools_dict)}")


    discovered_mcp_tools_dict: Dict[str, ToolDefinition] = {}
    if agent.mcp_servers:
        server_list = sorted(list(set(agent.mcp_servers)))
        server_list_tuple = tuple(server_list)
        config_str = json.dumps(config, sort_keys=True)

        try:
            discovered_mcp_tools_dict = await _discover_tools_cached(agent.name, server_list_tuple, config_str)
        except RuntimeError as e:
            if "cannot reuse already awaited coroutine" in str(e):
                logger.warning(f"Caught RuntimeError during tool discovery for '{agent.name}', likely due to async cache interaction. Clearing cache and retrying once.")
                _discover_tools_cached.cache_clear()
                logger.info(f"Cache cleared for _discover_tools_cached due to RuntimeError.")
                try:
                    discovered_mcp_tools_dict = await _discover_tools_cached(agent.name, server_list_tuple, config_str)
                except Exception as retry_e:
                     logger.exception(f"Error during MCP tool discovery retry for agent '{agent.name}': {retry_e}")
            else:
                 raise e
        except Exception as e:
             logger.exception(f"General error during MCP tool discovery call for agent '{agent.name}': {e}")


    logger.debug(f"[DEBUG] Agent '{agent.name}' - Unique discovered MCP tools: {len(discovered_mcp_tools_dict)}")
    final_tools_dict = {**static_tools_dict, **discovered_mcp_tools_dict}

    logger.info(f"Agent '{agent.name}' total unique functions/tools merged: {len(final_tools_dict)}")
    return list(final_tools_dict.values())


def format_tools_for_llm(tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
    """Formats the ToolDefinition list into the structure expected by OpenAI API."""
    if not tools:
        return []
    try:
        formatted_tools = [tool.model_dump(exclude_none=True) for tool in tools]
        for ft in formatted_tools:
            if ft.get("type") == "function" and "function" in ft and isinstance(ft["function"], dict):
                 func_details = ft["function"]
                 if "parameters" in func_details and isinstance(func_details["parameters"], dict):
                      if "properties" not in func_details["parameters"]:
                           func_details["parameters"]["properties"] = {}
                      if "properties" in func_details["parameters"] and "type" not in func_details["parameters"]:
                           func_details["parameters"]["type"] = "object"

        if not isinstance(formatted_tools, list) or not all(isinstance(t, dict) for t in formatted_tools):
             logger.error("Formatted tools are not a list of dictionaries.")
             return []

        return formatted_tools
    except Exception as e:
         logger.exception(f"Error formatting tools for LLM: {e}")
         return []


async def execute_mcp_tool(
    agent_name: str,
    config: Dict[str, Any],
    mcp_server_list: List[str],
    tool_name: str,
    tool_arguments: Dict[str, Any],
    tool_call_id: str,
    timeout: int = 120,
    max_response_tokens: int = 4096
) -> ToolResult:
    """Executes a tool via MCP, finding the correct server."""
    from ...types import ToolResult # Local import to avoid circular dependency if ToolResult moves

    logger.info(f"Attempting MCP execution for tool '{tool_name}' requested by agent '{agent_name}'. Tool Call ID: {tool_call_id}")
    logger.debug(f"Tool arguments (redacted): {redact_sensitive_data(tool_arguments)}")

    target_server_name = None
    original_tool_name = tool_name

    if MCP_SEPARATOR in tool_name:
        parts = tool_name.split(MCP_SEPARATOR, 1)
        potential_server = parts[0]
        original_tool_name = parts[1]
        if potential_server in config.get("mcpServers", {}) and potential_server in mcp_server_list:
            target_server_name = potential_server
            logger.debug(f"Tool name '{tool_name}' indicates target server: '{target_server_name}'. Original tool name: '{original_tool_name}'")
        else:
            logger.warning(f"Tool name '{tool_name}' prefix '{potential_server}' doesn't match a valid, assigned MCP server. Searching all assigned servers.")

    if not target_server_name:
         logger.debug(f"Tool name '{tool_name}' not prefixed or prefix invalid. Searching assigned servers: {mcp_server_list}")
         # TODO: Implement a more robust lookup if tool name is not prefixed.
         if MCP_SEPARATOR not in tool_name:
              logger.error(f"Cannot execute unprefixed tool '{tool_name}' via MCP without robust lookup. Execution failed.")
              return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: MCP execution failed - Tool name '{tool_name}' needs server prefix.")

    if not target_server_name:
         logger.error(f"Could not determine target MCP server for tool '{tool_name}'. Execution failed.")
         return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: MCP execution failed - Cannot find server for tool '{tool_name}'.")

    server_config = config.get("mcpServers", {}).get(target_server_name)
    if not server_config:
         logger.error(f"Configuration for target MCP server '{target_server_name}' not found.")
         return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: MCP execution failed - Server '{target_server_name}' not configured.")

    port = server_config.get("port", MCP_DEFAULT_PORT)
    base_url = f"http://127.0.0.1:{port}"
    api_path = f"/tools/{original_tool_name}"

    logger.info(f"Executing tool '{original_tool_name}' on server '{target_server_name}' at {base_url}{api_path}")

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=float(timeout)) as client:
            response = await client.post(api_path, json=tool_arguments)
            response.raise_for_status()

            try:
                result_content = response.json()
                if isinstance(result_content, dict) and "content" in result_content:
                     content = result_content["content"]
                elif isinstance(result_content, str):
                     content = result_content
                else:
                     content = json.dumps(result_content)

                if isinstance(content, str) and content.startswith(f"HANDOFF{MCP_SEPARATOR}"):
                     logger.info(f"Received handoff signal from MCP tool '{tool_name}'.")
                else:
                    content_str = content if isinstance(content, str) else json.dumps(content)
                    estimated_tokens = len(content_str.split())
                    if estimated_tokens > max_response_tokens:
                         logger.warning(f"MCP tool response for '{tool_name}' exceeds token limit ({estimated_tokens} > {max_response_tokens}). Truncating.")
                         content = content_str[:max_response_tokens * 5] + "... (truncated)"

                logger.info(f"Successfully executed MCP tool '{tool_name}'.")
                return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=content)

            except json.JSONDecodeError:
                logger.warning(f"MCP tool '{tool_name}' executed but response was not valid JSON. Returning raw text.")
                raw_content = response.text
                estimated_tokens = len(raw_content.split())
                if estimated_tokens > max_response_tokens:
                    logger.warning(f"MCP tool response (raw) for '{tool_name}' exceeds token limit ({estimated_tokens} > {max_response_tokens}). Truncating.")
                    raw_content = raw_content[:max_response_tokens * 5] + "... (truncated)"
                return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=raw_content)

    except httpx.TimeoutException:
        logger.error(f"Timeout executing MCP tool '{tool_name}' on server '{target_server_name}'.")
        return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: MCP tool '{tool_name}' timed out.")
    except httpx.RequestError as e:
        logger.error(f"HTTP error executing MCP tool '{tool_name}' on {target_server_name}: {e}")
        return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: Failed to connect to MCP server for tool '{tool_name}'.")
    except httpx.HTTPStatusError as e:
         logger.error(f"HTTP status error executing MCP tool '{tool_name}' on {target_server_name}: {e.response.status_code}")
         error_content = f"Error: MCP tool '{tool_name}' failed with status {e.response.status_code}."
         try:
              error_detail = e.response.json()
              if isinstance(error_detail, dict) and "detail" in error_detail:
                   error_content += f" Detail: {error_detail['detail']}"
              else: error_content += f" Response: {e.response.text[:200]}"
         except json.JSONDecodeError: error_content += f" Response: {e.response.text[:200]}"
         return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=error_content)
    except Exception as e:
        logger.exception(f"Unexpected error executing MCP tool '{tool_name}' on {target_server_name}: {e}")
        return ToolResult(tool_call_id=tool_call_id, name=tool_name, content=f"Error: Unexpected error executing MCP tool '{tool_name}'.")

