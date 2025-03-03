"""
Swarm Core Module

This module defines the Swarm class, responsible for initializing the Swarm framework,
managing agents, and orchestrating conversations with LLM endpoints and MCP servers.
Supports asynchronous operations and dynamic tool discovery.
"""

import os
import copy
import inspect
import json
import logging
import uuid
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
from .utils.general_utils import serialize_datetime
from .utils.message_utils import filter_duplicate_system_messages, filter_messages, update_null_content
from .utils.context_utils import get_token_count, truncate_message_history

# Configure module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Always enable debug for detailed tracing
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Constants
__CTX_VARS_NAME__ = "context_variables"
GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("SWARM_MAX_CONTEXT_TOKENS", 8000))

class ChatMessage(SimpleNamespace):
    """Simplified chat message structure with default values."""
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
        """Serialize the message to JSON, omitting empty tool_calls."""
        d = self.__dict__.copy()
        if "tool_calls" in d and not d["tool_calls"]:
            del d["tool_calls"]
        return json.dumps(d)

_discovery_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

class Swarm:
    """Core class for managing agents and LLM interactions within the Swarm framework."""

    def __init__(self, client=None, config: Optional[dict] = None, debug: bool = False):
        """
        Initialize the Swarm instance with LLM configuration and client.

        Args:
            client: Optional pre-initialized AsyncOpenAI client.
            config: Configuration dictionary for LLMs and MCP servers.
            debug: Enable debug logging if True.
        """
        self.model = os.getenv("DEFAULT_LLM", "default")
        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.config = config or {}
        self.debug = debug

        # Context limits
        self.max_context_messages = 50
        self.max_context_tokens = GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS
        self.summarize_threshold_tokens = int(self.max_context_tokens * 0.75)
        self.keep_recent_tokens = int(self.max_context_tokens * 0.25)

        # Load LLM configuration with environment-specific overrides
        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
            if self.model == "default" and os.getenv("OPENAI_API_KEY"):
                self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                logger.debug(
                    f"Overriding default API key with OPENAI_API_KEY for model '{self.model}': "
                    f"{redact_sensitive_data(self.current_llm_config['api_key'])}"
                )
        except ValueError:
            logger.warning(f"LLM config for '{self.model}' not found. Falling back to 'default'.")
            self.current_llm_config = load_llm_config(self.config, "default")
            if os.getenv("OPENAI_API_KEY"):
                self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                logger.debug(
                    f"Overriding default API key with OPENAI_API_KEY for fallback model 'default': "
                    f"{redact_sensitive_data(self.current_llm_config['api_key'])}"
                )

        # Fallback to dummy key if no API key is provided and not suppressed
        if not self.current_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            self.current_llm_config["api_key"] = "sk-DUMMYKEY"
            logger.debug("No API key provided—using dummy key 'sk-DUMMYKEY'")

        # Initialize the AsyncOpenAI client
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(
            f"Initializing AsyncOpenAI client with model='{self.model}', "
            f"base_url='{client_kwargs.get('base_url', 'default')}', "
            f"api_key={redacted_kwargs['api_key']}"
        )
        self.client = client or AsyncOpenAI(**client_kwargs)

        logger.info(f"Swarm initialized with max_context_tokens={self.max_context_tokens}")

    def register_agent_functions_with_nemo(self, agent: Agent) -> None:
        """Register agent functions with NeMo Guardrails if configured."""
        if not getattr(agent, "nemo_guardrails_instance", None) and getattr(agent, "nemo_guardrails_config", None):
            config_path = f"nemo_guardrails/{agent.nemo_guardrails_config}/config.yml"
            try:
                from nemoguardrails.guardrails import Guardrails
                agent.nemo_guardrails_instance = Guardrails.from_yaml(config_path)
                logger.debug(f"Initialized NeMo Guardrails for agent '{agent.name}'.")
            except Exception as e:
                logger.error(f"Failed to initialize NeMo Guardrails for '{agent.name}': {e}")
                return

        if not agent.functions or not getattr(agent, "nemo_guardrails_instance", None):
            logger.debug(f"No functions or NeMo instance for agent '{agent.name}'. Skipping registration.")
            return

        for func in agent.functions:
            action_name = getattr(func, '__name__', None) or getattr(func, '__qualname__', None)
            if not action_name:
                logger.warning(f"Skipping function registration for '{agent.name}': no name attribute.")
                continue
            try:
                agent.nemo_guardrails_instance.runtime.register_action(func, name=action_name)
                logger.debug(f"Registered function '{action_name}' with NeMo Guardrails for '{agent.name}'.")
            except Exception as e:
                logger.error(f"Failed to register function '{action_name}' for '{agent.name}': {e}")

    async def discover_and_merge_agent_tools(self, agent: Agent, debug: bool = False) -> List[AgentFunction]:
        """Discover and merge tools from MCP servers with agent's static functions."""
        logger.debug(f"Discovering tools for agent '{agent.name}'")
        if not agent.mcp_servers:
            funcs = agent.functions or []
            logger.debug(f"Agent '{agent.name}' has no MCP servers. Returning static functions: {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in funcs]}")
            return funcs

        discovered_tools = []
        for server_name in agent.mcp_servers:
            logger.debug(f"Discovering tools from MCP server '{server_name}' for '{agent.name}'.")
            server_config = self.config.get("mcpServers", {}).get(server_name, {})
            if not server_config:
                logger.warning(f"MCP server '{server_name}' not found in config.")
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
                logger.error(f"Failed to discover tools from '{server_name}' for '{agent.name}': {e}")

        all_functions = (agent.functions or []) + discovered_tools
        logger.debug(f"Total functions for '{agent.name}': {len(all_functions)} (Static: {len(agent.functions or [])}, Discovered: {len(discovered_tools)})")
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
        """Retrieve a chat completion from the LLM for the given agent and history."""
        logger.debug(f"Generating chat completion for agent '{agent.name}'")
        active_model = model_override or self.current_llm_config.get("model", self.model)
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(
            f"Using client with model='{active_model}', "
            f"base_url='{client_kwargs.get('base_url', 'default')}', "
            f"api_key={redacted_kwargs['api_key']}"
        )

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
        logger.debug(f"Tools for '{agent.name}': {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in agent.functions]}")

        create_params = {
            "model": active_model,
            "messages": messages,
            "stream": stream,
            "temperature": self.current_llm_config.get("temperature", self.temperature),
        }
        if tools:
            create_params["tools"] = tools
            create_params["tool_choice"] = agent.tool_choice or self.tool_choice
        if getattr(agent, "response_format", None):
            create_params["response_format"] = agent.response_format

        create_params = {k: v for k, v in create_params.items() if v is not None}
        logger.debug(f"Chat completion params: model='{active_model}', messages_count={len(messages)}, stream={stream}")

        try:
            if agent.nemo_guardrails_instance and messages[-1].get('content'):
                self.register_agent_functions_with_nemo(agent)
                options = GenerationOptions(llm_params={"temperature": 0.5}, llm_output=True, output_vars=True, return_context=True)
                logger.debug(f"Using NeMo Guardrails for '{agent.name}'")
                response = agent.nemo_guardrails_instance.generate(messages=update_null_content(messages), options=options)
                logger.debug(f"NeMo Guardrails response received for '{agent.name}'")
                return response
            else:
                logger.debug(f"Calling OpenAI API for '{agent.name}' with model='{active_model}'")
                prev_openai_api_key = os.environ.pop("OPENAI_API_KEY", None)
                try:
                    completion = await self.client.chat.completions.create(**create_params)
                finally:
                    if prev_openai_api_key is not None:
                        os.environ["OPENAI_API_KEY"] = prev_openai_api_key
                logger.debug(f"OpenAI completion received for '{agent.name}'")
                return completion.choices[0].message
        except OpenAIError as e:
            logger.error(f"Chat completion failed for '{agent.name}': {e}")
            raise

    async def get_chat_completion_message(self, **kwargs) -> ChatCompletionMessage:
        """Wrapper to extract and handle chat completion message."""
        logger.debug("Fetching chat completion message")
        completion = await self.get_chat_completion(**kwargs)
        if isinstance(completion, ChatCompletionMessage):
            return completion
        logger.debug(f"Unexpected completion type: {type(completion)}. Converting to message.")
        return ChatMessage(content=str(completion))

    def handle_function_result(self, result: Any, debug: bool) -> Result:
        """Process the result of a tool call into a standardized Result object."""
        logger.debug("Processing function result")
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
        """Execute tool calls and aggregate results."""
        logger.debug("Handling tool calls")
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

        logger.debug("Tool calls processed")
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
        """Run the swarm in streaming mode, yielding responses incrementally."""
        logger.debug(f"Starting streaming run for agent '{agent.name}'")
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        context_variables["active_agent_name"] = active_agent.name
        active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug)

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
                    active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug)
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected.")

                logger.debug(f"Generating response after tool calls for '{active_agent.name}'")
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

        logger.debug(f"Streaming run completed with {len(history[init_len:])} new messages")
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
        """Execute the swarm run, supporting both streaming and non-streaming modes."""
        logger.debug(f"Starting run for agent '{agent.name}'")
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
        active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug)

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
                    active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug)
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected.")

                logger.debug(f"Generating response after tool calls for '{active_agent.name}'")
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

        logger.debug(f"Run completed with {len(history[init_len:])} new messages")
        return Response(id=f"response-{uuid.uuid4()}", messages=history[init_len:], agent=active_agent, context_variables=context_variables)

    def validate_message_sequence(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure tool messages correspond to valid tool calls."""
        logger.debug("Validating message sequence")
        valid_tool_call_ids = {tc["id"] for msg in messages if msg.get("role") == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        return [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """Repair message sequence by reordering tool messages after their calls."""
        logger.debug(f"Repairing message payload with {len(messages)} messages")
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
