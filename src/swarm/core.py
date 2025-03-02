"""
Swarm Core Module

This module encapsulates the core functionality of the Swarm framework, orchestrating agent interactions,
tool discovery, and message handling with a focus on performance and extensibility. It manages the lifecycle
of agent-driven conversations, integrating with MCP servers and LLM clients asynchronously for seamless,
non-blocking execution.

Key Components:
- Swarm: Central class for agent management and conversation orchestration.
- Tool Discovery: Asynchronous integration with MCP servers for dynamic tool loading.
- Message Processing: Robust handling of chat completions, tool calls, and context variables.
"""

import os
import copy
import datetime
import inspect
import json
import logging
import uuid
import re
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

# Configure logging for detailed diagnostics and traceability
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Locks for discovery to prevent redundant calls
_discovery_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

__CTX_VARS_NAME__ = "context_variables"

# Global default context limits
GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("SWARM_MAX_CONTEXT_TOKENS", 8000))


# --- Utility Functions ---
def serialize_datetime(obj):
    """Convert datetime objects to ISO format for JSON serialization."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def filter_duplicate_system_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate system messages, keeping only the first occurrence."""
    filtered = []
    system_found = False
    for msg in messages:
        if msg["role"] == "system":
            if system_found:
                continue
            system_found = True
        filtered.append(msg)
    return filtered


def filter_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out messages with no content."""
    return [msg for msg in messages if msg.get('content') is not None]


def update_null_content(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace null content with empty strings in messages."""
    for msg in messages:
        if msg.get('content') is None:
            msg['content'] = ""
    return messages


def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """Calculate total token count for messages using tiktoken."""
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return sum(len(encoding.encode(msg.get("content", ""))) for msg in messages)


def truncate_message_history(
    messages: List[Dict[str, Any]], 
    model: str, 
    max_tokens: Optional[int] = None,
    max_messages: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Truncate message history to fit within token or message limits, preserving the original instruction."""
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    max_tokens = max_tokens if max_tokens is not None else int(os.getenv("MAX_OUTPUT", GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS))
    total_tokens = get_token_count(messages, model)

    # If within limits, return unchanged
    if total_tokens <= max_tokens and (max_messages is None or len(messages) <= max_messages):
        return messages

    # Keep original instruction (first message assumed as system)
    truncated = [messages[0]] if messages and messages[0].get("role") == "system" else []
    remaining_messages = messages[1:] if messages and messages[0].get("role") == "system" else messages
    current_tokens = get_token_count(truncated, model)

    # Apply message limit if specified
    if max_messages and len(remaining_messages) > (max_messages - len(truncated)):
        remaining_messages = remaining_messages[-(max_messages - len(truncated)):]

    # Build from newest to oldest within token limit
    for msg in reversed(remaining_messages):
        msg_tokens = len(encoding.encode(msg.get("content", "")))
        if current_tokens + msg_tokens <= max_tokens:
            truncated.insert(len(truncated) if not truncated else 1, msg)  # After system message
            current_tokens += msg_tokens
        else:
            if truncated and truncated[0].get("role") == "system":
                truncated[0]["content"] += "..."  # Indicate truncation
            break

    return truncated


async def summarize_older_messages(
    messages: List[Dict[str, Any]],
    model: str,
    threshold_tokens: int,
    keep_recent_tokens: int,
    swarm: 'Swarm'
) -> List[Dict[str, Any]]:
    """Summarize older messages when context exceeds threshold, keeping recent messages and original instruction."""
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    total_tokens = get_token_count(messages, model)
    if total_tokens <= threshold_tokens:
        return messages

    # Keep original instruction (first message assumed as system)
    original = [messages[0]] if messages and messages[0].get("role") == "system" else []
    remaining_messages = messages[1:] if messages and messages[0].get("role") == "system" else messages

    # Keep recent messages within keep_recent_tokens
    recent_messages = []
    recent_tokens = 0
    for msg in reversed(remaining_messages):
        msg_tokens = len(encoding.encode(msg.get("content", "")))
        if recent_tokens + msg_tokens <= keep_recent_tokens:
            recent_messages.insert(0, msg)
            recent_tokens += msg_tokens
        else:
            break

    # Messages to summarize
    to_summarize = [msg for msg in remaining_messages if msg not in recent_messages]
    if not to_summarize:
        return messages

    summary_prompt = [
        {"role": "system", "content": "Summarize the following conversation concisely, focusing on key points."},
        {"role": "user", "content": "\n".join([f"{msg['role']}: {msg['content']}" for msg in to_summarize])}
    ]
    summary_response = await swarm.get_chat_completion(
        agent=Agent(name="summarizer", instructions="Summarize concisely."),
        history=summary_prompt,
        context_variables={},
        debug=DEBUG
    )
    summary = summary_response.content if summary_response.content else "Summary unavailable..."

    # Reconstruct history: original instruction + summary + recent messages
    new_history = original
    new_history.append({"role": "system", "content": f"Summary of earlier conversation: {summary}..."})
    new_history.extend(recent_messages)
    return new_history


# --- Message Classes ---
class ChatMessage(SimpleNamespace):
    """A lightweight message object for chat completions."""
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


# --- Swarm Class ---
class Swarm:
    """
    Core class for managing agents, tools, and conversations in the Swarm framework.

    This class orchestrates interactions between agents, MCP servers, and the LLM client,
    providing async methods for chat completions, tool execution, and message handling.
    It ensures efficient, non-blocking operation with robust error handling and caching.

    Attributes:
        model (str): Default LLM model identifier.
        client (AsyncOpenAI): Async client for OpenAI API interactions.
        agents (Dict[str, Agent]): Registry of available agents.
        config (dict): Swarm configuration dictionary.
        current_llm_config (dict): Active LLM configuration.
    """

    def __init__(self, client=None, config: Optional[dict] = None):
        """
        Initialize the Swarm with an optional client and configuration.

        Args:
            client (AsyncOpenAI, optional): Pre-existing OpenAI client instance.
            config (dict, optional): Configuration dictionary for LLM and MCP settings.
        """
        self.model = os.getenv("DEFAULT_LLM", "default")
        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.config = config or {}
        logger.debug(f"Initializing Swarm with model: {self.model}")

        # Load context management settings from config (blueprint level for messages only)
        blueprint_config = self.config.get("blueprints", {}).get("nsh", {})  # Default to 'nsh' for now
        self.max_context_messages = blueprint_config.get("max_context_messages", 50)

        # Load LLM configuration
        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
        except ValueError:
            logger.warning(f"LLM config for '{self.model}' not found. Using 'default'.")
            self.current_llm_config = load_llm_config(self.config, "default")

        if not self.current_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            self.current_llm_config["api_key"] = "sk-DUMMYKEY"

        # Load model-specific context settings with global default
        self.max_context_tokens = self.current_llm_config.get("max_context_tokens", GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS)
        self.summarize_threshold_tokens = self.current_llm_config.get("summarize_threshold_tokens", int(self.max_context_tokens * 0.75))
        self.keep_recent_tokens = self.current_llm_config.get("keep_recent_tokens", int(self.max_context_tokens * 0.25))

        # Initialize async OpenAI client
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(f"Initializing AsyncOpenAI client with kwargs: {redacted_kwargs}")
        self.client = client or AsyncOpenAI(**client_kwargs)

        logger.info(f"Swarm initialized successfully with max_context_tokens={self.max_context_tokens}, "
                    f"summarize_threshold_tokens={self.summarize_threshold_tokens}, "
                    f"keep_recent_tokens={self.keep_recent_tokens}, max_context_messages={self.max_context_messages}")

    def register_agent_functions_with_nemo(self, agent: Agent) -> None:
        """Register agent functions with NeMo Guardrails if configured."""
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
        """Discover and merge tools from MCP servers for an agent asynchronously, updating agent.functions."""
        if not agent.mcp_servers:
            logger.debug(f"Agent '{agent.name}' has no MCP servers assigned.")
            return agent.functions

        base_timeout = 10
        total_timeout = min(20, base_timeout * len(agent.mcp_servers))
        logger.debug(f"Discovery timeout set to {total_timeout}s for {len(agent.mcp_servers)} servers.")

        async def discover_tools_from_server(server_name: str) -> List[Tool]:
            async with _discovery_locks[server_name]:
                logger.debug(f"Discovering tools from MCP server '{server_name}' for agent '{agent.name}'.")
                server_config = self.config.get("mcpServers", {}).get(server_name, {})
                if not server_config:
                    logger.warning(f"MCP server '{server_name}' not in config.")
                    return []
                try:
                    provider = MCPToolProvider.get_instance(server_name, server_config, total_timeout)
                    tools = await provider.discover_tools(agent)
                    for tool in tools:
                        if not hasattr(tool, "requires_approval"):
                            tool.requires_approval = True
                    logger.debug(f"Discovered {len(tools)} tools from '{server_name}': {[t.name for t in tools if hasattr(t, 'name')]}")
                    return tools
                except Exception as e:
                    logger.error(f"Failed to discover tools from '{server_name}': {e}")
                    return []

        tasks = [discover_tools_from_server(server_name) for server_name in agent.mcp_servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        discovered_tools = []
        for result in results:
            if isinstance(result, list):
                discovered_tools.extend(result)

        all_functions = agent.functions + discovered_tools
        agent.functions = all_functions
        logger.debug(f"Total functions for '{agent.name}': {len(all_functions)} (Existing: {len(agent.functions)}, Discovered: {len(discovered_tools)})")
        if debug:
            logger.debug(f"[DEBUG] Existing: {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in agent.functions]}")
            logger.debug(f"[DEBUG] Discovered: {[t.name for t in discovered_tools if hasattr(t, 'name')]}")
            logger.debug(f"[DEBUG] Combined: {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in all_functions]}")
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
        """Asynchronously fetch a chat completion from the OpenAI API or NeMo Guardrails with context management."""
        new_llm_config = self.config.get("llm", {}).get(agent.model or "default", {})
        if not new_llm_config:
            logger.warning(f"LLM config for '{agent.model}' not found. Using 'default'.")
            new_llm_config = self.config.get("llm", {}).get("default", {})

        if not new_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            new_llm_config["api_key"] = "sk-DUMMYKEY"

        active_model = model_override or new_llm_config.get("model", self.model)
        self.max_context_tokens = new_llm_config.get("max_context_tokens", GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS)
        self.summarize_threshold_tokens = new_llm_config.get("summarize_threshold_tokens", int(self.max_context_tokens * 0.75))
        self.keep_recent_tokens = new_llm_config.get("keep_recent_tokens", int(self.max_context_tokens * 0.25))

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
        messages = await summarize_older_messages(messages, active_model, self.summarize_threshold_tokens, self.keep_recent_tokens, self)

        tools = [function_to_json(f, truncate_desc=True) for f in agent.functions if hasattr(f, "name") and f.name]

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
                return response
            else:
                logger.debug(f"Using OpenAI Completion for '{agent.name}'")
                completion = await self.client.chat.completions.create(**create_params)
                return completion.choices[0].message
        except OpenAIError as e:
            if "context length" in str(e).lower():
                logger.warning(f"Context length exceeded: {e}. Truncating and retrying...")
                messages = truncate_message_history(messages, active_model, int(self.max_context_tokens * 0.75))
                create_params["messages"] = messages
                try:
                    completion = await self.client.chat.completions.create(**create_params)
                    return completion.choices[0].message
                except OpenAIError as retry_e:
                    logger.error(f"Retry failed after truncation: {retry_e}")
                    raise
            else:
                logger.error(f"Chat completion failed: {e}")
                raise

    async def get_chat_completion_message(self, **kwargs) -> ChatCompletionMessage:
        """Extract the chat completion message asynchronously."""
        completion = await self.get_chat_completion(**kwargs)
        if isinstance(completion, ChatCompletionMessage):
            return completion
        logger.debug(f"Unexpected completion type: {type(completion)}. Treating as message: {completion}")
        return ChatMessage(content=str(completion))

    def handle_function_result(self, result: Any, debug: bool) -> Result:
        """Convert function results into a standardized Result object."""
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
        """Handle tool calls asynchronously, executing functions and updating context."""
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
                if getattr(func, "dynamic", False):
                    raw_result = await func(**args)
                else:
                    raw_result = func(**args)
                    if inspect.iscoroutine(raw_result):
                        raw_result = await raw_result

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
        """Run the swarm with streaming output, handling agent transitions asynchronously."""
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

            if not message.tool_calls or not execute_tools:
                break

            tool_calls = [ChatCompletionMessageToolCall(id=tc["id"], function=Function(**tc["function"]), type=tc["type"]) for tc in message.tool_calls]
            partial_response = await self.handle_tool_calls(tool_calls, active_agent.functions, context_variables, debug)
            history.extend(partial_response.messages)
            context_variables.update(partial_response.context_variables)

            if partial_response.agent:
                active_agent = partial_response.agent
                active_agent.functions = await self.discover_and_merge_agent_tools(active_agent, debug=debug)

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
        """Run the swarm asynchronously, returning a response or streaming generator."""
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
                    continue
            break

        return Response(id=f"response-{uuid.uuid4()}", messages=history[init_len:], agent=active_agent, context_variables=context_variables)

    def validate_message_sequence(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter message sequence for consistency."""
        valid_tool_call_ids = {tc["id"] for msg in messages if msg["role"] == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        return [msg for msg in messages if msg["role"] != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """Repair message payload by deduplicating and reordering."""
        messages = filter_duplicate_system_messages(messages)
        valid_tool_call_ids = {tc["id"] for msg in messages if msg["role"] == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        repaired = [msg for msg in messages if msg["role"] != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

        final_sequence = []
        i = 0
        while i < len(repaired):
            msg = repaired[i]
            if msg["role"] == "assistant" and "tool_calls" in msg:
                tool_call_ids = [tc["id"] for tc in msg["tool_calls"]]
                final_sequence.append(msg)
                j = i + 1
                tool_msgs = []
                while j < len(repaired):
                    if repaired[j]["role"] == "tool" and repaired[j].get("tool_call_id") in tool_call_ids:
                        tool_msgs.append(repaired.pop(j))
                    else:
                        j += 1
                final_sequence.extend(tool_msgs)
            else:
                final_sequence.append(msg)
            i += 1

        if debug:
            logger.debug(f"[DEBUG] Repaired payload: {json.dumps(final_sequence, indent=2, default=str)}")
        return final_sequence
