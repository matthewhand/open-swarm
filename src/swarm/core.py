import os
import json
import logging
import asyncio
from typing import List, Dict, Optional, Union, AsyncGenerator, Any
from openai import AsyncOpenAI, OpenAIError
import uuid

from .types import Agent, LLMConfig, Response, ToolCall, ToolResult, ChatMessage
from .settings import Settings
# Import the loader function directly
from .extensions.config.config_loader import load_llm_config
from .utils.redact import redact_sensitive_data
from .llm.chat_completion import get_chat_completion_message
from .extensions.mcp.mcp_utils import execute_mcp_tool, discover_tools_for_agent, format_tools_for_llm
from .extensions.mcp.mcp_constants import MCP_SEPARATOR
from .utils.context_utils import get_token_count

settings = Settings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Ensure DEBUG level for detailed logs
log_handler = logging.StreamHandler()
formatter = logging.Formatter(settings.log_format.value)
log_handler.setFormatter(formatter)
if not logger.handlers: logger.addHandler(log_handler)
logger.debug(f"Swarm Core initialized with log level: {settings.log_level.upper()}")

class Swarm:
    def __init__(
        self,
        llm_profile: str = "default",
        config: Optional[dict] = None,
        api_key: Optional[str] = None, # Explicit override (Highest Prio)
        base_url: Optional[str] = None,# Explicit override
        model: Optional[str] = None,   # Explicit override
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
        self.agents = agents or {}; logger.debug(f"Initial agents: {list(self.agents.keys())}")
        self.config = config or {} # Store original config if needed elsewhere
        logger.debug(f"INIT START: Received api_key arg: {'****' if api_key else 'None'}")

        # --- Simplified Config Loading Order v7 ---
        # 1. Determine profile name
        llm_profile_name = os.getenv("DEFAULT_LLM", llm_profile)
        logger.debug(f"INIT: Using LLM profile name: '{llm_profile_name}'")

        # 2. Load config (load_llm_config handles internal priorities: config+placeholder > specific_env > openai_env > dummy)
        try:
            loaded_config_dict = load_llm_config(self.config, llm_profile_name)
            logger.debug(f"INIT: Config received from load_llm_config for '{llm_profile_name}': {redact_sensitive_data(loaded_config_dict)}")
        except Exception as e:
             logger.critical(f"INIT: Failed to load config for profile '{llm_profile_name}': {e}", exc_info=True); raise

        # 3. Apply explicit overrides from __init__ args (Highest Priority)
        final_config = loaded_config_dict.copy() # Start with loaded config
        log_key_source = final_config.get("_log_key_source", "load_llm_config") # Get source from loader

        if api_key is not None:
            if final_config.get('api_key') != api_key: logger.debug("INIT: Overriding API key with explicit __init__ arg.")
            final_config['api_key'] = api_key
            log_key_source = "__init__ arg" # Explicit arg overrides source log
        if base_url is not None:
            if final_config.get('base_url') != base_url: logger.debug("INIT: Overriding base_url with explicit __init__ arg.")
            final_config['base_url'] = base_url
        if model is not None:
            if final_config.get('model') != model: logger.debug("INIT: Overriding model with explicit __init__ arg.")
            final_config['model'] = model

        # 4. Store the final config and derived attributes
        self.current_llm_config = final_config
        self.model = self.current_llm_config.get("model")
        self.provider = self.current_llm_config.get("provider")
        # --- End Simplified Config Loading ---

        self.max_context_tokens=max_context_tokens; self.max_context_messages=max_context_messages
        self.max_tool_response_tokens=max_tool_response_tokens; self.max_total_tool_response_tokens=max_total_tool_response_tokens
        self.max_tool_calls_per_turn=max_tool_calls_per_turn; self.tool_execution_timeout=tool_execution_timeout
        self.tool_discovery_timeout=tool_discovery_timeout

        # --- Initialize Client using the final self.current_llm_config ---
        client_kwargs = {"api_key": self.current_llm_config.get("api_key"), "base_url": self.current_llm_config.get("base_url")}
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs)
        try:
            self.client = AsyncOpenAI(**client_kwargs)
            final_api_key_used = self.current_llm_config.get("api_key") # Log the key actually used
            logger.info(f"Swarm initialized. LLM Profile: '{llm_profile_name}', Loaded Model: '{self.model}', API Key Source: {log_key_source}, Final API Key Used: {'****' if final_api_key_used else 'None'}")
            if self.debug: logger.debug(f"AsyncOpenAI client initialized with kwargs: {redacted_kwargs}")
        except Exception as e: logger.critical(f"Failed to initialize OpenAI client: {e}", exc_info=True); raise

    # ... (Rest of Swarm class methods unchanged) ...
    def register_agent(self, agent: Agent):
        if agent.name in self.agents: logger.warning(f"Agent '{agent.name}' already registered. Overwriting.")
        self.agents[agent.name] = agent; logger.info(f"Agent '{agent.name}' registered.")
        if self.debug: logger.debug(f"Agent details: {agent}")

    async def _execute_tool_call(self, agent: Agent, tool_call: ToolCall, context_variables: Dict[str, Any]) -> ToolResult:
        function_name = tool_call.function.name; tool_call_id = tool_call.id
        logger.info(f"Executing tool call '{function_name}' (ID: {tool_call_id}) for agent '{agent.name}'.")
        arguments = {}; content = f"Error: Tool '{function_name}' execution failed."
        try: arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
        except json.JSONDecodeError as e: logger.error(f"JSONDecodeError args for {function_name}: {e}"); content=f"Error: Invalid JSON args: {e}"
        func_executed = False
        if hasattr(agent, 'functions') and agent.functions:
            for func in agent.functions:
                if callable(func) and func.__name__ == function_name:
                    logger.debug(f"Executing Python func: {function_name}"); func_executed = True
                    try:
                        result = await func(**arguments) if asyncio.iscoroutinefunction(func) else func(**arguments)
                        if function_name.startswith("handoff_to_") and isinstance(result, Agent): logger.info(f"Handoff to '{result.name}'"); content = f"HANDOFF{MCP_SEPARATOR}{result.name}"
                        else: content = json.dumps(result, default=str)
                    except Exception as e: logger.error(f"Error in Python func {function_name}: {e}", exc_info=True); content=f"Error: {e}"
                    break
        if not func_executed and agent.mcp_servers:
            logger.debug(f"Checking MCP servers for {function_name}: {agent.mcp_servers}"); func_executed = True
            mcp_result = await execute_mcp_tool(agent_name=agent.name, config=self.config, mcp_server_list=agent.mcp_servers, tool_name=function_name, tool_arguments=arguments, tool_call_id=tool_call_id, timeout=self.tool_execution_timeout, max_response_tokens=self.max_tool_response_tokens)
            content = mcp_result.content
        if not func_executed: logger.error(f"Tool '{function_name}' not found for agent '{agent.name}'."); content=f"Error: Tool not available."
        if isinstance(content, str) and not content.startswith(f"HANDOFF{MCP_SEPARATOR}"):
             token_count = get_token_count(content, self.current_llm_config.get("model") or "gpt-4")
             if token_count > self.max_tool_response_tokens: logger.warning(f"Truncating tool response {function_name}. Size: {token_count} > Limit: {self.max_tool_response_tokens}"); content = content[:self.max_tool_response_tokens * 4] + "... (truncated)"
        return ToolResult(tool_call_id=tool_call_id, name=function_name, content=content)

    async def _run_non_streaming(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, debug: bool = False) -> Response:
        current_agent = agent; history = list(messages); context_vars = context_variables.copy() if context_variables else {}; turn = 0
        while turn < max_turns:
            turn += 1; logger.debug(f"Turn {turn} starting with agent '{current_agent.name}'.")
            discovered_tools_defs = await discover_tools_for_agent(current_agent, self.config); formatted_tools = format_tools_for_llm(discovered_tools_defs)
            if debug and formatted_tools: logger.debug(f"Tools passed to LLM: {len(formatted_tools)}")
            try:
                ai_message_dict = await get_chat_completion_message(client=self.client, agent=current_agent, history=history, context_variables=context_vars, current_llm_config=self.current_llm_config, max_context_tokens=self.max_context_tokens, max_context_messages=self.max_context_messages, tools=formatted_tools or None, tool_choice="auto" if formatted_tools else None, stream=False, debug=debug)
                ai_message_dict["sender"] = current_agent.name; history.append(ai_message_dict)
                tool_calls_raw = ai_message_dict.get("tool_calls")
                if tool_calls_raw:
                    if not isinstance(tool_calls_raw, list): tool_calls_raw = []
                    logger.info(f"Agent '{current_agent.name}' requested {len(tool_calls_raw)} tool calls.")
                    tool_calls_to_execute = [ToolCall(**tc_raw) for tc_raw in tool_calls_raw[:self.max_tool_calls_per_turn] if isinstance(tc_raw, dict)]
                    if len(tool_calls_raw) > self.max_tool_calls_per_turn: logger.warning(f"Clamping tool calls.")
                    tool_tasks = [self._execute_tool_call(current_agent, tc, context_vars) for tc in tool_calls_to_execute]
                    tool_results: List[ToolResult] = await asyncio.gather(*tool_tasks)
                    next_agent_name_from_handoff = None; total_tool_response_tokens = 0
                    for result in tool_results:
                        history.append(result.model_dump(exclude_none=True)); content = result.content
                        if isinstance(content, str):
                            if content.startswith(f"HANDOFF{MCP_SEPARATOR}"):
                                parts = content.split(MCP_SEPARATOR); potential_next_agent = parts[1] if len(parts) > 1 else None
                                if potential_next_agent and potential_next_agent in self.agents:
                                     if not next_agent_name_from_handoff: next_agent_name_from_handoff = potential_next_agent; logger.info(f"Handoff to '{next_agent_name_from_handoff}' confirmed.")
                                     elif next_agent_name_from_handoff != potential_next_agent: logger.warning("Multiple different handoffs requested.")
                                else: logger.warning(f"Handoff to unknown agent '{potential_next_agent}'.")
                            else: total_tool_response_tokens += get_token_count(content, self.current_llm_config.get("model") or "gpt-4")
                    if total_tool_response_tokens > self.max_total_tool_response_tokens: logger.error(f"Total tool tokens ({total_tool_response_tokens}) exceeded limit."); history.append({"role": "assistant", "content": "[System Error: Tool responses exceeded token limit.]"}); break
                    if next_agent_name_from_handoff: current_agent = self.agents[next_agent_name_from_handoff]; context_vars["active_agent_name"] = current_agent.name; logger.debug(f"Activating agent '{current_agent.name}'."); continue
                    else: continue
                else: break
            except OpenAIError as e: logger.error(f"API error turn {turn}: {e}", exc_info=True); history.append({"role": "assistant", "content": f"[System Error: API call failed]"}); break
            except Exception as e: logger.error(f"Error turn {turn}: {e}", exc_info=True); history.append({"role": "assistant", "content": f"[System Error: Unexpected error]"}); break
        if turn >= max_turns: logger.warning(f"Reached max turns ({max_turns}).")
        logger.debug(f"Non-streaming run completed. Turns={turn}, History={len(history)}.")
        last_user_idx = next((i for i in range(len(history) - 1, -1, -1) if history[i].get("role") == "user"), -1)
        final_responses_raw = history[last_user_idx + 1:] if last_user_idx != -1 else history
        final_responses_typed = [ChatMessage(**msg) if isinstance(msg, dict) else msg for msg in final_responses_raw]
        response_id = f"response-{uuid.uuid4()}"
        return Response(id=response_id, messages=final_responses_typed, agent=current_agent, context_variables=context_vars)

    async def _run_streaming(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, debug: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        current_agent = agent; history = list(messages); context_vars = context_variables.copy() if context_variables else {}
        logger.debug(f"Streaming run starting with agent '{current_agent.name}'.")
        discovered_tools_defs = await discover_tools_for_agent(current_agent, self.config); formatted_tools = format_tools_for_llm(discovered_tools_defs)
        if debug and formatted_tools: logger.debug(f"Tools passed to LLM for '{current_agent.name}': {len(formatted_tools)}")
        try:
            stream_generator = await get_chat_completion_message(client=self.client, agent=current_agent, history=history, context_variables=context_vars, current_llm_config=self.current_llm_config, max_context_tokens=self.max_context_tokens, max_context_messages=self.max_context_messages, tools=formatted_tools or None, tool_choice="auto" if formatted_tools else None, stream=True, debug=debug)
            async for chunk in stream_generator: yield chunk
            logger.warning("Tool calls and handoffs are not processed in streaming mode.")
        except OpenAIError as e: logger.error(f"API error stream: {e}", exc_info=True); yield {"error": f"API call failed: {str(e)}"}
        except Exception as e: logger.error(f"Error stream: {e}", exc_info=True); yield {"error": f"Unexpected error: {str(e)}"}
        logger.debug(f"Streaming run finished for agent '{current_agent.name}'.")

    async def run(self, agent: Agent, messages: List[Dict[str, Any]], context_variables: Optional[Dict[str, Any]] = None, max_turns: int = 10, stream: bool = False, debug: bool = False) -> Union[Response, AsyncGenerator[Dict[str, Any], None]]:
        effective_debug = debug or self.debug
        if effective_debug: logger.setLevel(logging.DEBUG); [h.setLevel(logging.DEBUG) for h in logger.handlers]
        if stream: return self._run_streaming(agent, messages, context_variables, max_turns, effective_debug)
        else: return await self._run_non_streaming(agent, messages, context_variables, max_turns, effective_debug)

