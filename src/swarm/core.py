import os
import json
import logging
import asyncio
import re # Import re for tool name validation in provider
from typing import List, Dict, Optional, Union, AsyncGenerator, Any, Callable
from openai import AsyncOpenAI, OpenAIError
import uuid

from .types import Agent, LLMConfig, Response, ToolCall, ToolResult, ChatMessage, Tool
from .settings import Settings
from .extensions.config.config_loader import load_server_config, load_llm_config, get_server_params # Import load_server_config
from .utils.redact import redact_sensitive_data
from .llm.chat_completion import get_chat_completion_message
from .extensions.mcp.mcp_tool_provider import MCPToolProvider
from .utils.context_utils import get_token_count

settings = Settings()
logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level.upper())
if not logger.handlers and not logging.getLogger().handlers:
    log_handler = logging.StreamHandler()
    formatter = logging.Formatter(settings.log_format.value)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

logger.debug(f"Swarm Core initialized with log level: {settings.log_level.upper()}")

# --- FIX: Define correct separator ---
MCP_TOOL_SEPARATOR = "__"

# --- Helper Function: Discover and Merge Agent Tools ---
async def discover_and_merge_agent_tools(agent: Agent, config: Dict[str, Any], timeout: int, debug: bool) -> List[Tool]:
    """
    Discovers tools from MCP servers listed in agent.mcp_servers and merges
    them with the agent's static functions. Returns a list of Tool objects.
    """
    merged_tools: Dict[str, Tool] = {}

    # 1. Process static functions
    if hasattr(agent, 'functions') and agent.functions:
        for func in agent.functions:
            if isinstance(func, Tool):
                if func.name in merged_tools: logger.warning(f"Duplicate tool name '{func.name}'. Overwriting.")
                merged_tools[func.name] = func
            elif callable(func):
                tool_name = getattr(func, '__name__', f'callable_{uuid.uuid4().hex[:6]}')
                if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", tool_name): # Validate static tool name
                     logger.warning(f"Static function name '{tool_name}' violates OpenAI pattern. Skipping.")
                     continue
                if tool_name in merged_tools: logger.warning(f"Duplicate static tool name '{tool_name}'. Overwriting.")

                docstring = getattr(func, '__doc__', None)
                description = docstring.strip() if docstring else f"Executes the {tool_name} function."

                input_schema = {"type": "object", "properties": {}}
                merged_tools[tool_name] = Tool(name=tool_name, func=func, description=description, input_schema=input_schema)
            else: logger.warning(f"Ignoring non-callable item in agent functions list: {func}")
    logger.debug(f"Agent '{agent.name}': Processed {len(merged_tools)} static tools.")

    # 2. Discover tools from MCP servers
    if agent.mcp_servers:
        mcp_server_configs = config.get("mcpServers", {})
        discovery_tasks = []
        for server_name in agent.mcp_servers:
            if server_name not in mcp_server_configs:
                logger.warning(f"Config for MCP server '{server_name}' for agent '{agent.name}' not found. Skipping.")
                continue
            server_config = mcp_server_configs[server_name]
            if not get_server_params(server_config, server_name):
                 logger.error(f"Invalid config for MCP server '{server_name}'. Cannot discover.")
                 continue
            try:
                 provider = MCPToolProvider.get_instance(server_name=server_name, server_config=server_config, timeout=timeout, debug=debug)
                 if provider.client: discovery_tasks.append(provider.discover_tools(agent))
                 else: logger.error(f"MCPClient failed init for '{server_name}'.")
            except Exception as e: logger.error(f"Error getting MCP instance for '{server_name}': {e}", exc_info=True)

        if discovery_tasks:
            logger.debug(f"Awaiting discovery from {len(discovery_tasks)} MCP providers.")
            results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception): logger.error(f"MCP discovery error: {result}")
                elif isinstance(result, list):
                    for mcp_tool in result:
                        if mcp_tool.name in merged_tools: logger.warning(f"Duplicate tool name '{mcp_tool.name}' (MCP vs Static/Other MCP). Overwriting.")
                        merged_tools[mcp_tool.name] = mcp_tool # Name already prefixed by provider
                else: logger.warning(f"Unexpected result type during MCP discovery: {type(result)}")

    final_tool_list = list(merged_tools.values())
    logger.info(f"Agent '{agent.name}': Final merged tool count: {len(final_tool_list)}")
    if debug: logger.debug(f"Agent '{agent.name}': Final tools: {[t.name for t in final_tool_list]}")
    return final_tool_list

# --- Helper Function: Format Tools for LLM ---
def format_tools_for_llm(tools: List[Tool]) -> List[Dict[str, Any]]:
    """Formats the Tool list into the structure expected by OpenAI API."""
    if not tools: return []
    formatted = []
    for tool in tools:
        parameters = tool.input_schema or {"type": "object", "properties": {}}
        if not isinstance(parameters, dict) or "type" not in parameters:
            logger.warning(f"Invalid schema for tool '{tool.name}'. Using default. Schema: {parameters}")
            parameters = {"type": "object", "properties": {}}
        elif parameters.get("type") == "object" and "properties" not in parameters:
             parameters["properties"] = {}

        # Validate tool name again before formatting
        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", tool.name):
             logger.error(f"Tool name '{tool.name}' is invalid for OpenAI API. Skipping.")
             continue

        formatted.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Executes the {tool.name} tool.",
                "parameters": parameters,
            },
        })
    return formatted

# --- Swarm Class ---
class Swarm:
    def __init__(
        self,
        llm_profile: str = "default",
        config: Optional[dict] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        agents: Optional[Dict[str, Agent]] = None,
        max_context_tokens: int = 8000,
        max_context_messages: int = 50,
        max_tool_response_tokens: int = 4096,
        max_total_tool_response_tokens: int = 16384,
        max_tool_calls_per_turn: int = 10,
        tool_execution_timeout: int = 120,
        tool_discovery_timeout: int = 15,
        debug: bool = False,
    ):
        self.debug = debug or settings.debug
        if self.debug: logger.setLevel(logging.DEBUG); [h.setLevel(logging.DEBUG) for h in logging.getLogger().handlers if hasattr(h, 'setLevel')] ; logger.debug("Debug mode enabled.")
        self.tool_execution_timeout = tool_execution_timeout
        self.tool_discovery_timeout = tool_discovery_timeout
        self.agents = agents or {}; logger.debug(f"Initial agents: {list(self.agents.keys())}")
        # Load config if not provided
        self.config = config if config is not None else load_server_config()
        logger.debug(f"INIT START: Received api_key arg: {'****' if api_key else 'None'}")

        llm_profile_name = os.getenv("DEFAULT_LLM", llm_profile)
        logger.debug(f"INIT: Using LLM profile name: '{llm_profile_name}'")
        try:
            loaded_config_dict = load_llm_config(self.config, llm_profile_name)
        except Exception as e: logger.critical(f"INIT: Failed to load config for profile '{llm_profile_name}': {e}", exc_info=True); raise

        final_config = loaded_config_dict.copy(); log_key_source = final_config.get("_log_key_source", "load_llm_config")
        if api_key is not None: final_config['api_key'] = api_key; log_key_source = "__init__ arg"
        if base_url is not None: final_config['base_url'] = base_url
        if model is not None: final_config['model'] = model
        self.current_llm_config = final_config; self.model = self.current_llm_config.get("model"); self.provider = self.current_llm_config.get("provider")

        self.max_context_tokens=max_context_tokens; self.max_context_messages=max_context_messages
        self.max_tool_response_tokens=max_tool_response_tokens; self.max_total_tool_response_tokens=max_total_tool_response_tokens
        self.max_tool_calls_per_turn=max_tool_calls_per_turn

        client_kwargs = {"api_key": self.current_llm_config.get("api_key"), "base_url": self.current_llm_config.get("base_url")}
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        try:
            self.client = AsyncOpenAI(**client_kwargs)
            final_api_key_used = self.current_llm_config.get("api_key")
            logger.info(f"Swarm initialized. LLM Profile: '{llm_profile_name}', Model: '{self.model}', Key Source: {log_key_source}, Key Used: {'****' if final_api_key_used else 'None'}")
            if self.debug: logger.debug(f"AsyncOpenAI client kwargs: {redact_sensitive_data(client_kwargs)}")
        except Exception as e: logger.critical(f"Failed to initialize OpenAI client: {e}", exc_info=True); raise
        self._agent_tools: Dict[str, List[Tool]] = {}

    def register_agent(self, agent: Agent):
        if agent.name in self.agents: logger.warning(f"Agent '{agent.name}' already registered. Overwriting.")
        self.agents[agent.name] = agent; logger.info(f"Agent '{agent.name}' registered.")
        if agent.name in self._agent_tools: del self._agent_tools[agent.name]
        if self.debug: logger.debug(f"Agent details: {agent}")

    async def _get_agent_tools(self, agent: Agent) -> List[Tool]:
         if agent.name not in self._agent_tools:
              logger.debug(f"Tools cache miss for agent '{agent.name}'. Discovering...")
              self._agent_tools[agent.name] = await discover_and_merge_agent_tools(agent, self.config, self.tool_discovery_timeout, self.debug)
         return self._agent_tools[agent.name]

    async def _execute_tool_call(self, agent: Agent, tool_call: ToolCall, context_variables: Dict[str, Any]) -> ToolResult:
        """Executes a single tool call, handling static and MCP tools."""
        function_name = tool_call.function.name # This is the name LLM used (could be prefixed)
        tool_call_id = tool_call.id
        logger.info(f"Executing tool call '{function_name}' (ID: {tool_call_id}) for agent '{agent.name}'.")
        arguments = {}
        content = f"Error: Tool '{function_name}' execution failed."

        try:
            args_raw = tool_call.function.arguments
            arguments = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            if not isinstance(arguments, dict):
                 logger.error(f"Parsed tool args for {function_name} not dict: {type(arguments)}. Args: {args_raw}")
                 raise ValueError("Tool arguments must be a JSON object.")
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError parsing args for {function_name}: {e}. Args: {args_raw}")
            content = f"Error: Invalid JSON args for '{function_name}': {e}"
        except ValueError as e: # Catch the explicit error from above
             content = str(e)
        except Exception as e:
             logger.error(f"Error processing args for {function_name}: {e}", exc_info=True)
             content = f"Error processing args for '{function_name}'."

        tool_executed = False
        if isinstance(arguments, dict): # Proceed only if args are valid
            agent_tools = await self._get_agent_tools(agent)
            target_tool: Optional[Tool] = next((t for t in agent_tools if t.name == function_name), None)

            if target_tool and callable(target_tool.func):
                tool_executed = True
                logger.debug(f"Found tool '{function_name}'. Executing...")
                try:
                    if asyncio.iscoroutinefunction(target_tool.func):
                        result = await asyncio.wait_for(target_tool.func(**arguments), timeout=self.tool_execution_timeout)
                    else:
                        # Consider running sync functions in threadpool executor
                        result = target_tool.func(**arguments)

                    # Process result
                    if isinstance(result, Agent):
                         logger.info(f"Handoff signal: Result is Agent '{result.name}'.")
                         # --- FIX: Use correct separator ---
                         content = f"HANDOFF{MCP_TOOL_SEPARATOR}{result.name}"
                    elif isinstance(result, (dict, list, tuple)): content = json.dumps(result, default=str)
                    elif result is None: content = "Tool executed successfully with no return value."
                    else: content = str(result)
                    logger.debug(f"Tool '{function_name}' executed. Raw result type: {type(result)}")

                except asyncio.TimeoutError:
                    logger.error(f"Timeout executing tool '{function_name}'.")
                    content = f"Error: Tool '{function_name}' timed out ({self.tool_execution_timeout}s)."
                except Exception as e:
                    logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                    content = f"Error: Tool '{function_name}' failed: {e}"
            # else: Tool not found error handled below

        if not tool_executed and isinstance(arguments, dict):
             logger.error(f"Tool '{function_name}' not found for agent '{agent.name}'. Available: {[t.name for t in await self._get_agent_tools(agent)]}")
             content = f"Error: Tool '{function_name}' not available for agent '{agent.name}'."

        # Truncation
        # --- FIX: Use correct separator ---
        if isinstance(content, str) and not content.startswith(f"HANDOFF{MCP_TOOL_SEPARATOR}"):
             token_count = get_token_count(content, self.current_llm_config.get("model"))
             if token_count > self.max_tool_response_tokens:
                  logger.warning(f"Truncating tool response '{function_name}'. Size: {token_count} > Limit: {self.max_tool_response_tokens}")
                  content = content[:self.max_tool_response_tokens * 4] + "... (truncated)"

        return ToolResult(tool_call_id=tool_call_id, name=function_name, content=content)

    async def _run_non_streaming(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, debug: bool = False) -> Response:
        current_agent = agent; history = list(messages); context_vars = context_variables.copy() if context_variables else {}; turn = 0
        while turn < max_turns:
            turn += 1; logger.debug(f"Turn {turn} starting with agent '{current_agent.name}'.")
            agent_tools = await self._get_agent_tools(current_agent); formatted_tools = format_tools_for_llm(agent_tools)
            if debug and formatted_tools: logger.debug(f"Tools for '{current_agent.name}': {[t['function']['name'] for t in formatted_tools]}")
            try:
                ai_message_dict = await get_chat_completion_message(client=self.client, agent=current_agent, history=history, context_variables=context_vars, current_llm_config=self.current_llm_config, max_context_tokens=self.max_context_tokens, max_context_messages=self.max_context_messages, tools=formatted_tools or None, tool_choice="auto" if formatted_tools else None, stream=False, debug=debug)
                ai_message_dict["sender"] = current_agent.name; history.append(ai_message_dict)
                tool_calls_raw = ai_message_dict.get("tool_calls")
                if tool_calls_raw:
                    if not isinstance(tool_calls_raw, list): tool_calls_raw = []
                    logger.info(f"Agent '{current_agent.name}' requested {len(tool_calls_raw)} tool calls.")
                    tool_calls_to_execute = []
                    for tc_raw in tool_calls_raw[:self.max_tool_calls_per_turn]:
                        try:
                             if isinstance(tc_raw, dict) and 'function' in tc_raw and isinstance(tc_raw['function'], dict) and 'name' in tc_raw['function'] and 'arguments' in tc_raw['function']: tool_calls_to_execute.append(ToolCall(**tc_raw))
                             else: logger.warning(f"Skipping malformed tool call: {tc_raw}")
                        except Exception as p_err: logger.warning(f"Skipping tool call validation error: {p_err}. Raw: {tc_raw}")
                    if len(tool_calls_raw) > self.max_tool_calls_per_turn: logger.warning(f"Clamping tool calls to {self.max_tool_calls_per_turn}.")

                    tool_tasks = [self._execute_tool_call(current_agent, tc, context_vars) for tc in tool_calls_to_execute]
                    tool_results: List[ToolResult] = await asyncio.gather(*tool_tasks)
                    next_agent_name_from_handoff = None; total_tool_response_tokens = 0
                    for result in tool_results:
                        history.append(result.model_dump(exclude_none=True)); content = result.content
                        if isinstance(content, str):
                             # --- FIX: Use correct separator ---
                            if content.startswith(f"HANDOFF{MCP_TOOL_SEPARATOR}"):
                                parts = content.split(MCP_TOOL_SEPARATOR, 1); potential_next_agent = parts[1] if len(parts) > 1 else None
                                if potential_next_agent and potential_next_agent in self.agents:
                                     if not next_agent_name_from_handoff: next_agent_name_from_handoff = potential_next_agent; logger.info(f"Handoff to '{next_agent_name_from_handoff}' confirmed.")
                                     elif next_agent_name_from_handoff != potential_next_agent: logger.warning(f"Multiple handoffs requested. Using first '{next_agent_name_from_handoff}'.")
                                else: logger.warning(f"Handoff to unknown agent '{potential_next_agent}'. Ignoring.")
                            else: total_tool_response_tokens += get_token_count(content, self.current_llm_config.get("model"))
                    if total_tool_response_tokens > self.max_total_tool_response_tokens: logger.error(f"Total tool tokens ({total_tool_response_tokens}) exceeded limit. Ending run."); history.append({"role": "assistant", "sender": "System", "content": "[System Error: Tool responses token limit exceeded.]"}); break
                    if next_agent_name_from_handoff: current_agent = self.agents[next_agent_name_from_handoff]; context_vars["active_agent_name"] = current_agent.name; logger.debug(f"Activating agent '{current_agent.name}'."); continue
                    else: continue
                else: break # No tool calls, end interaction
            except OpenAIError as e: logger.error(f"API error turn {turn} for '{current_agent.name}': {e}", exc_info=True); history.append({"role": "assistant", "sender": "System", "content": f"[System Error: API call failed]"}); break
            except Exception as e: logger.error(f"Unexpected error turn {turn} for '{current_agent.name}': {e}", exc_info=True); history.append({"role": "assistant", "sender": "System", "content": f"[System Error: Unexpected error]"}); break
        if turn >= max_turns: logger.warning(f"Reached max turns ({max_turns}).")
        logger.debug(f"Non-streaming run completed. Turns={turn}, History Messages={len(history)}.")
        final_messages_raw = history[len(messages):]; final_messages_typed = [ChatMessage(**msg) for msg in final_messages_raw if isinstance(msg, dict)]
        response_id = f"response-{uuid.uuid4()}"
        return Response(id=response_id, messages=final_messages_typed, agent=current_agent, context_variables=context_vars)

    async def _run_streaming(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, debug: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        current_agent = agent; history = list(messages); context_vars = context_variables.copy() if context_variables else {}; logger.debug(f"Streaming run starting for '{current_agent.name}'. (Tool exec/handoff N/A)")
        agent_tools = await self._get_agent_tools(current_agent); formatted_tools = format_tools_for_llm(agent_tools)
        if debug and formatted_tools: logger.debug(f"Tools for '{current_agent.name}' (streaming): {[t['function']['name'] for t in formatted_tools]}")
        try:
            stream_generator = get_chat_completion_message(client=self.client, agent=current_agent, history=history, context_variables=context_vars, current_llm_config=self.current_llm_config, max_context_tokens=self.max_context_tokens, max_context_messages=self.max_context_messages, tools=formatted_tools or None, tool_choice="auto" if formatted_tools else None, stream=True, debug=debug)
            async for chunk in stream_generator: yield chunk
            logger.warning("Tool calls/handoffs not processed in streaming.")
        except OpenAIError as e: logger.error(f"API error stream for '{current_agent.name}': {e}", exc_info=True); yield {"error": f"API call failed: {str(e)}"}
        except Exception as e: logger.error(f"Error stream for '{current_agent.name}': {e}", exc_info=True); yield {"error": f"Unexpected error: {str(e)}"}
        logger.debug(f"Streaming run finished for '{current_agent.name}'.")

    async def run(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, stream: bool = False, debug: bool = False) -> Union[Response, AsyncGenerator[Dict[str, Any], None]]:
        effective_debug = debug or self.debug
        if effective_debug != logger.isEnabledFor(logging.DEBUG):
             new_level = logging.DEBUG if effective_debug else settings.log_level.upper(); logger.setLevel(new_level); [h.setLevel(new_level) for h in logger.handlers]; logger.debug(f"Log level set to {new_level}.")
        if not agent: raise ValueError("Agent cannot be None")
        if not isinstance(messages, list): raise TypeError("Messages must be a list")
        logger.info(f"Starting {'STREAMING' if stream else 'NON-STREAMING'} run with agent '{agent.name}'")
        if stream: return self._run_streaming(agent, messages, context_variables, max_turns, effective_debug)
        else: return await self._run_non_streaming(agent, messages, context_variables, max_turns, effective_debug)
