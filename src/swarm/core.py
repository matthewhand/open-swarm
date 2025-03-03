"""
Swarm Core Module

Handles the initialization of the Swarm, agent management, and orchestration
of conversations between agents and MCP servers with async support.
"""

import os
import copy
import datetime
import inspect
import json
import logging
import uuid
import tiktoken
from collections import defaultdict
from typing import List, Optional, Dict, Any, Callable
from types import SimpleNamespace
from nemoguardrails.rails.llm.options import GenerationOptions

import asyncio
from openai import AsyncOpenAI, OpenAIError

from .util import function_to_json, merge_chunk
from .types import (
    Agent,
    AgentFunction,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    Function,
    Response,
    Result,
    Tool,
)
from .extensions.config.config_loader import load_llm_config
from .extensions.mcp.mcp_tool_provider import MCPToolProvider
from .settings import DEBUG
from .utils.redact import redact_sensitive_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

__CTX_VARS_NAME__ = "context_variables"
GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("SWARM_MAX_CONTEXT_TOKENS", 8000))

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def filter_duplicate_system_messages(messages):
    filtered = []
    system_found = False
    for msg in messages:
        if msg.get("role") == "system":
            if system_found:
                continue
            system_found = True
        filtered.append(msg)
    return filtered

def filter_messages(messages):
    return [msg for msg in messages if msg.get('content') is not None]

def update_null_content(messages):
    for msg in messages:
        if msg.get('content') is None:
            msg['content'] = ""
    return messages

def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Encoding not found for model '{model}'. Using 'cl100k_base'.")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    total_tokens = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total_tokens += len(encoding.encode(content))
        # Only add structural tokens for real models, not dummy
        if model != "dummy-model":
            total_tokens += 4  # Estimate for role and structure
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                total_tokens += len(encoding.encode(json.dumps(tool_call)))
    logger.debug(f"Total token count: {total_tokens}")
    return total_tokens

def truncate_message_history(messages: List[Dict[str, Any]], model: str, max_tokens: Optional[int] = None, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Truncate message history to fit within token and message limits.
    Defaults to MAX_OUTPUT env var or 8000 for max_tokens, and 50 for max_messages if not provided.
    Removes messages from the beginning until within limits.
    """
    if not messages:
        logger.debug("No messages to truncate.")
        return messages

    # Set defaults if arguments are not provided
    max_tokens = max_tokens if max_tokens is not None else int(os.getenv("MAX_OUTPUT", GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS))
    max_messages = max_messages if max_messages is not None else 50

    # Separate system messages
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    non_system_messages = [msg for msg in messages if msg.get("role") != "system"]

    current_token_count = get_token_count(non_system_messages, model)
    if len(non_system_messages) <= max_messages and current_token_count <= max_tokens:
        logger.debug(f"Message history within limits: {len(non_system_messages)} messages, {current_token_count} tokens")
        return system_messages + non_system_messages

    # Truncate non-system messages from the beginning
    truncated = non_system_messages[:]
    while len(truncated) > 0 and (get_token_count(truncated, model) > max_tokens or len(truncated) > max_messages):
        token_count = get_token_count(truncated, model)
        if token_count > max_tokens:
            truncated.pop(0)
        elif len(truncated) > max_messages:
            truncated = truncated[-max_messages:]
        # Recheck conditions after each removal
        token_count = get_token_count(truncated, model)
        if token_count <= max_tokens and len(truncated) <= max_messages:
            break

    final_messages = system_messages + truncated
    final_token_count = get_token_count(final_messages, model)
    logger.debug(f"Truncated to {len(final_messages)} messages with {final_token_count} tokens")
    return final_messages

class ChatMessage(SimpleNamespace):
    def __init__(self, **kwargs):
        defaults = {
            "role": "assistant",
            "content": "",
            "sender": "assistant",
            "function_call": kwargs.get("function_call", None),
            "tool_calls": kwargs.get("tool_calls", [])
        }
        super().__init__(**(defaults | kwargs))

    def model_dump_json(self) -> str:
        d = self.__dict__.copy()
        if "tool_calls" in d and not d["tool_calls"]:
            del d["tool_calls"]
        return json.dumps(d)

_discovery_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

class Swarm:
    def __init__(self, client=None, config: Optional[dict] = None, debug: bool = False):
        self.model = os.getenv("DEFAULT_LLM", "default")
        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.config = config or {}
        self.debug = debug
        logger.debug(f"Initializing Swarm with model={self.model}, debug={debug}")

        self.max_context_messages = 50
        self.max_context_tokens = GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS
        self.summarize_threshold_tokens = int(self.max_context_tokens * 0.75)
        self.keep_recent_tokens = int(self.max_context_tokens * 0.25)

        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
        except ValueError:
            logger.warning(f"LLM config for '{self.model}' not found. Using 'default'.")
            self.current_llm_config = load_llm_config(self.config, "default")

        if not self.current_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            self.current_llm_config["api_key"] = "sk-DUMMYKEY"

        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(f"Initializing AsyncOpenAI client with kwargs: {redacted_kwargs}")
        self.client = client or AsyncOpenAI(**client_kwargs)

        logger.info(f"Swarm initialized successfully with max_context_tokens={self.max_context_tokens}")

    def register_agent_functions_with_nemo(self, agent: Agent) -> None:
        if not getattr(agent, "nemo_guardrails_instance", None) and getattr(agent, "nemo_guardrails_config", None):
            config_path = f"nemo_guardrails/{agent.nemo_guardrails_config}/config.yml"
            try:
                from nemoguardrails.guardrails import Guardrails
                agent.nemo_guardrails_instance = Guardrails.from_yaml(config_path)
                logger.debug(f"Initialized NeMo Guardrails for agent '{agent.name}'.")
            except Exception as e:
                logger.error(f"Failed to initialize NeMo Guardrails: {e}")
                return

        if not agent.functions or not getattr(agent, "nemo_guardrails_instance", None):
            logger.debug(f"No functions or NeMo instance for agent '{agent.name}'. Skipping registration.")
            return

        for func in agent.functions:
            action_name = getattr(func, '__name__', None) or getattr(func, '__qualname__', None)
            if not action_name:
                logger.warning(f"Skipping function registration for agent '{agent.name}': no name attribute.")
                continue
            try:
                agent.nemo_guardrails_instance.runtime.register_action(func, name=action_name)
                logger.debug(f"Registered function '{action_name}' with NeMo Guardrails.")
            except Exception as e:
                logger.error(f"Failed to register function '{action_name}': {e}")

    async def discover_and_merge_agent_tools(self, agent: Agent, debug: bool = False) -> List[AgentFunction]:
        if not agent.mcp_servers:
            logger.debug(f"Agent '{agent.name}' has no assigned MCP servers.")
            return agent.functions or []

        discovered_tools = []
        for server_name in agent.mcp_servers:
            logger.debug(f"Discovering tools from MCP server '{server_name}' for agent '{agent.name}'.")
            server_config = self.config.get("mcpServers", {}).get(server_name, {})
            if not server_config:
                logger.warning(f"MCP server '{server_name}' not in config.")
                continue
            try:
                provider = MCPToolProvider.get_instance(server_name, server_config, timeout=15, debug=debug)
                tools = await provider.discover_tools(agent)
                for tool in tools:
                    if not hasattr(tool, "requires_approval"):
                        tool.requires_approval = True
                discovered_tools.extend(tools)
                logger.debug(f"Discovered {len(tools)} tools from '{server_name}': {[t.name for t in tools if hasattr(t, 'name')]}")
            except Exception as e:
                logger.error(f"Failed to discover tools from '{server_name}': {e}")

        all_functions = (agent.functions or []) + discovered_tools
        logger.debug(f"Total functions for '{agent.name}': {len(all_functions)} (Static: {len(agent.functions or [])}, Discovered: {len(discovered_tools)})")
        if debug:
            static_names = [getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in (agent.functions or [])]
            discovered_names = [t.name for t in discovered_tools if hasattr(t, 'name')]
            combined_names = [getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in all_functions]
            logger.debug(f"[DEBUG] Static: {static_names}")
            logger.debug(f"[DEBUG] Discovered: {discovered_names}")
            logger.debug(f"[DEBUG] Combined: {combined_names}")
        return all_functions

    async def get_chat_completion(
        self,
        agent: Agent,
        history: List[Dict[str, Any]],
        context_variables: dict,
        model_override: Optional[str] = None,
        stream: bool = False,
        debug: bool = False
    ) -> ChatCompletionMessage:
        logger.debug(f"Entering get_chat_completion for agent '{agent.name}'")
        
        new_llm_config = self.config.get("llm", {}).get(agent.model or "default", {})
        if not new_llm_config:
            logger.warning(f"LLM config for '{agent.model}' not found. Using 'default'.")
            new_llm_config = self.config.get("llm", {}).get("default", {})

        if not new_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            new_llm_config["api_key"] = "sk-DUMMYKEY"

        active_model = model_override or new_llm_config.get("model", self.model)
        old_config = self.current_llm_config or {}
        if (not old_config or
            old_config.get("base_url") != new_llm_config.get("base_url") or
            old_config.get("api_key") != new_llm_config.get("api_key")):
            client_kwargs = {k: v for k, v in {"api_key": new_llm_config.get("api_key"), "base_url": new_llm_config.get("base_url")}.items() if v}
            redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
            logger.debug(f"Reinitializing AsyncOpenAI client: {redacted_kwargs}")
            self.client = AsyncOpenAI(**client_kwargs)
        self.current_llm_config = new_llm_config.copy()

        context_variables = defaultdict(str, context_variables)
        instructions = agent.instructions(context_variables) if callable(agent.instructions) else agent.instructions
        messages = [{"role": "system", "content": instructions}]

        seen_ids = set()
        for msg in history:
            msg_id = msg.get("id", hash(json.dumps(msg, sort_keys=True, default=serialize_datetime)))
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                messages.append(msg)
        messages = filter_duplicate_system_messages(messages)
        messages = truncate_message_history(messages, active_model, self.max_context_tokens, self.max_context_messages)

        tools = [function_to_json(f, truncate_desc=True) for f in agent.functions]
        logger.debug(f"Tools provided to LLM for '{agent.name}': {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in agent.functions]}")

        create_params = {
            "model": active_model,
            "messages": messages,
            "stream": stream,
            "temperature": new_llm_config.get("temperature", self.temperature),
        }
        if tools:
            create_params["tools"] = tools
            create_params["tool_choice"] = agent.tool_choice or self.tool_choice
        if getattr(agent, "response_format", None):
            create_params["response_format"] = agent.response_format

        create_params = {k: v for k, v in create_params.items() if v is not None}

        if debug:
            logger.debug(f"[DEBUG] Chat completion payload: {json.dumps(create_params, indent=2, default=serialize_datetime)}")

        try:
            if agent.nemo_guardrails_instance and messages[-1].get('content'):
                self.register_agent_functions_with_nemo(agent)
                options = GenerationOptions(llm_params={"temperature": 0.5}, llm_output=True, output_vars=True, return_context=True)
                logger.debug(f"Using NeMo Guardrails for '{agent.name}'")
                response = agent.nemo_guardrails_instance.generate(messages=update_null_content(messages), options=options)
                logger.debug(f"NeMo Guardrails response received for '{agent.name}'")
                return response
            else:
                logger.debug(f"Using OpenAI Completion for '{agent.name}'")
                completion = await self.client.chat.completions.create(**create_params)
                logger.debug(f"OpenAI completion received for '{agent.name}'")
                return completion.choices[0].message
        except OpenAIError as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    async def get_chat_completion_message(self, **kwargs) -> ChatCompletionMessage:
        logger.debug("Entering get_chat_completion_message")
        completion = await self.get_chat_completion(**kwargs)
        logger.debug("Chat completion message extracted")
        if isinstance(completion, ChatCompletionMessage):
            return completion
        logger.debug(f"Unexpected completion type: {type(completion)}. Treating as message: {completion}")
        return ChatMessage(content=str(completion))

    def handle_function_result(self, result: Any, debug: bool) -> Result:
        logger.debug("Entering handle_function_result")
        match result:
            case Result() as result_obj:
                return result_obj
            case Agent() as agent:
                return Result(value=json.dumps({"assistant": agent.name}), agent=agent)
            case _:
                try:
                    return Result(value=str(result))
                except Exception as e:
                    logger.error(f"Failed to cast result to string: {e}")
                    raise TypeError(f"Cannot cast result to string: {result}. Error: {e}")

    async def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[AgentFunction],
        context_variables: dict,
        debug: bool
    ) -> Response:
        logger.debug("Entering handle_tool_calls")
        function_map = {getattr(f, "name", getattr(f, "__name__", "unnamed")): f for f in functions if getattr(f, "name", getattr(f, "__name__", None))}
        partial_response = Response(messages=[], agent=None, context_variables={})

        for tool_call in tool_calls:
            name = tool_call.function.name
            tool_call_id = tool_call.id

            if name not in function_map:
                logger.error(f"Tool '{name}' not found in function map.")
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": f"Error: Tool {name} not found."
                })
                continue

            func = function_map[name]
            args = json.loads(tool_call.function.arguments)
            if __CTX_VARS_NAME__ in func.__code__.co_varnames:
                args[__CTX_VARS_NAME__] = context_variables

            try:
                # Always await to handle both sync and async functions safely
                raw_result = func(**args)
                if inspect.isawaitable(raw_result):
                    logger.debug(f"Awaiting result for tool '{name}'")
                    raw_result = await raw_result
                else:
                    logger.debug(f"Executed sync tool '{name}'")

                result = self.handle_function_result(raw_result, debug)
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": json.dumps(result.value)
                })
                partial_response.context_variables.update(result.context_variables)
                if result.agent:
                    partial_response.agent = result.agent
                    context_variables["active_agent_name"] = result.agent.name
                    logger.debug(f"Switched to agent '{result.agent.name}'.")
            except Exception as e:
                logger.error(f"Error executing tool '{name}': {e}")
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": f"Error: {str(e)}"
                })

        logger.debug("Tool calls handled")
        return partial_response

    async def run_and_stream(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True
    ):
        logger.debug(f"Entering run_and_stream for agent '{agent.name}'")
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        context_variables["active_agent_name"] = active_agent.name
        active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug=debug)

        turn = 0
        while turn < max_turns:
            turn += 1
            message = ChatMessage(sender=active_agent.name)

            completion = await self.get_chat_completion(
                agent=active_agent, history=history, context_variables=context_variables,
                model_override=model_override, stream=True, debug=debug
            )

            yield {"delim": "start"}
            async for chunk in completion:
                delta = chunk.choices[0].delta
                merge_chunk(message, delta)
                yield delta
            yield {"delim": "end"}

            message.tool_calls = list(message.tool_calls.values()) or None
            history.append(json.loads(message.model_dump_json()))

            if message.tool_calls and execute_tools:
                tool_calls = [ChatCompletionMessageToolCall(id=tc["id"], function=Function(**tc["function"]), type=tc["type"]) for tc in message.tool_calls]
                partial_response = await self.handle_tool_calls(tool_calls, active_agent.functions, context_variables, debug)
                history.extend(partial_response.messages)
                context_variables.update(partial_response.context_variables)

                if partial_response.agent:
                    active_agent = partial_response.agent
                    active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug=debug)
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected. Continuing with new agent.")
                
                logger.debug(f"Generating LLM response after tool calls for '{active_agent.name}'")
                completion = await self.get_chat_completion(
                    agent=active_agent, history=history, context_variables=context_variables,
                    model_override=model_override, stream=True, debug=debug
                )
                message = ChatMessage(sender=active_agent.name)
                yield {"delim": "start"}
                async for chunk in completion:
                    delta = chunk.choices[0].delta
                    merge_chunk(message, delta)
                    yield delta
                yield {"delim": "end"}
                message.tool_calls = list(message.tool_calls.values()) or None
                history.append(json.loads(message.model_dump_json()))

                if not message.tool_calls:
                    break
            else:
                break

        logger.debug(f"Exiting run_and_stream with {len(history[init_len:])} new messages")
        yield {"response": Response(messages=history[init_len:], agent=active_agent, context_variables=context_variables)}

    async def run(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        stream: bool = False,
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True
    ) -> Response:
        logger.debug(f"Entering run for agent '{agent.name}'")
        if stream:
            return self.run_and_stream(
                agent=agent, messages=messages, context_variables=context_variables,
                model_override=model_override, debug=debug, max_turns=max_turns, execute_tools=execute_tools
            )

        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        context_variables["active_agent_name"] = active_agent.name
        active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug=debug)

        turn = 0
        while turn < max_turns:
            turn += 1
            message = await self.get_chat_completion_message(
                agent=active_agent, history=history, context_variables=context_variables,
                model_override=model_override, stream=False, debug=debug
            )
            message.sender = active_agent.name
            history.append(json.loads(message.model_dump_json()))

            if message.tool_calls and execute_tools:
                partial_response = await self.handle_tool_calls(message.tool_calls, active_agent.functions, context_variables, debug)
                history.extend(partial_response.messages)
                context_variables.update(partial_response.context_variables)
                if partial_response.agent:
                    active_agent = partial_response.agent
                    active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug=debug)
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected. Continuing with new agent.")
                
                logger.debug(f"Generating LLM response after tool calls for '{active_agent.name}'")
                message = await self.get_chat_completion_message(
                    agent=active_agent, history=history, context_variables=context_variables,
                    model_override=model_override, stream=False, debug=debug
                )
                message.sender = active_agent.name
                history.append(json.loads(message.model_dump_json()))

                if not message.tool_calls:
                    break
            else:
                break

        logger.debug(f"Exiting run with {len(history[init_len:])} new messages")
        return Response(id=f"response-{uuid.uuid4()}", messages=history[init_len:], agent=active_agent, context_variables=context_variables)

    def validate_message_sequence(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.debug("Entering validate_message_sequence")
        valid_tool_call_ids = {tc["id"] for msg in messages if msg.get("role") == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        return [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        logger.debug(f"Entering repair_message_payload with {len(messages)} messages")
        messages = filter_duplicate_system_messages(messages)
        valid_tool_call_ids = {tc["id"] for msg in messages if msg.get("role") == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        repaired = [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]
        final_sequence = []
        i = 0
        while i < len(repaired):
            msg = repaired[i]
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_call_ids = [tc["id"] for tc in msg["tool_calls"]]
                final_sequence.append(msg)
                j = i + 1
                tool_msgs = []
                while j < len(repaired):
                    if repaired[j].get("role") == "tool" and repaired[j].get("tool_call_id") in tool_call_ids:
                        tool_msgs.append(repaired.pop(j))
                    else:
                        j += 1
                final_sequence.extend(tool_msgs)
            else:
                final_sequence.append(msg)
            i += 1
        if debug:
            logger.debug(f"Repaired payload: {json.dumps(final_sequence, indent=2, default=str)}")
        return final_sequence

