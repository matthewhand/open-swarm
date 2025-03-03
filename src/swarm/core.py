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

# Moved from context_utils.py to avoid circular imports
def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """Calculate the total token count for a list of messages using the model's encoding."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Encoding not found for model '{model}'. Using 'cl100k_base' as fallback.")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    total_tokens = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total_tokens += len(encoding.encode(content))
        # Add approximate tokens for role and structure
        total_tokens += 4  # Rough estimate for role and separators
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                total_tokens += len(encoding.encode(json.dumps(tool_call)))
    logger.debug(f"Total token count for messages: {total_tokens}")
    return total_tokens

def truncate_message_history(messages: List[Dict[str, Any]], model: str, max_tokens: int, max_messages: int) -> List[Dict[str, Any]]:
    """
    Truncate message history to fit within token and message limits, preserving assistant-tool message pairs.
    """
    if not messages:
        logger.debug("No messages to truncate.")
        return messages

    # Separate system messages (preserve these)
    system_messages = [msg for msg in messages if msg["role"] == "system"]
    non_system_messages = [msg for msg in messages if msg["role"] != "system"]

    # Early exit if within limits
    current_token_count = get_token_count(messages, model)
    if len(non_system_messages) <= max_messages and current_token_count <= max_tokens:
        logger.debug(f"Message history within limits: {len(non_system_messages)} messages, {current_token_count} tokens")
        return messages

    # Pre-calculate token counts for each message
    message_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_messages]
    total_tokens = sum(tokens for _, tokens in message_tokens)

    # Truncate from oldest to newest, preserving assistant-tool pairs
    truncated = []
    i = len(message_tokens) - 1
    while i >= 0 and (len(truncated) < max_messages and total_tokens <= max_tokens):
        msg, tokens = message_tokens[i]
        if msg["role"] == "tool":
            # Look for preceding assistant message with matching tool_call_id
            tool_call_id = msg.get("tool_call_id")
            assistant_idx = i - 1
            assistant_found = False
            while assistant_idx >= 0:
                prev_msg, prev_tokens = message_tokens[assistant_idx]
                if prev_msg["role"] == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc["id"] == tool_call_id:
                            if total_tokens + prev_tokens <= max_tokens and len(truncated) + 2 <= max_messages:
                                truncated.insert(0, prev_msg)
                                truncated.insert(1, msg)
                                total_tokens += tokens + prev_tokens
                            assistant_found = True
                            break
                if assistant_found:
                    break
                assistant_idx -= 1
            if not assistant_found:
                logger.debug(f"Skipping orphaned tool message with tool_call_id '{tool_call_id}'")
        elif msg["role"] == "assistant" and "tool_calls" in msg:
            # Include assistant and all following tool messages
            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            tool_msgs = []
            j = i + 1
            while j < len(message_tokens):
                next_msg, next_tokens = message_tokens[j]
                if next_msg["role"] == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                    tool_msgs.append((next_msg, next_tokens))
                    tool_call_ids.remove(next_msg["tool_call_id"])
                else:
                    break
                j += 1
            if total_tokens + tokens + sum(t for _, t in tool_msgs) <= max_tokens and len(truncated) + 1 + len(tool_msgs) <= max_messages:
                truncated.insert(0, msg)
                for tool_msg, tool_tokens in tool_msgs:
                    truncated.insert(1, tool_msg)
                total_tokens += tokens + sum(t for _, t in tool_msgs)
            else:
                logger.debug(f"Skipping assistant message with tool_calls due to token/message limits")
        else:
            # Non-tool-related message
            if total_tokens + tokens <= max_tokens and len(truncated) < max_messages:
                truncated.insert(0, msg)
                total_tokens += tokens
        i -= 1

    final_messages = system_messages + truncated
    logger.debug(f"Truncated to {len(final_messages)} messages with {total_tokens} tokens")
    return final_messages

async def summarize_older_messages(messages: List[Dict[str, Any]], model: str, summarize_threshold_tokens: int, keep_recent_tokens: int, swarm: 'Swarm') -> List[Dict[str, Any]]:
    """Summarize older messages if the total token count exceeds the threshold, keeping recent messages intact."""
    total_tokens = get_token_count(messages, model)
    if total_tokens <= summarize_threshold_tokens:
        logger.debug(f"Total tokens ({total_tokens}) below threshold ({summarize_threshold_tokens}); no summarization needed.")
        return messages

    system_messages = [msg for msg in messages if msg["role"] == "system"]
    non_system_messages = [msg for msg in messages if msg["role"] != "system"]
    if not non_system_messages:
        return messages

    message_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_messages]
    recent_messages = []
    recent_token_count = 0
    i = len(message_tokens) - 1
    while i >= 0 and recent_token_count < keep_recent_tokens:
        msg, tokens = message_tokens[i]
        recent_messages.insert(0, msg)
        recent_token_count += tokens
        i -= 1

    older_messages = [msg for msg, _ in message_tokens[:i + 1]]
    if not older_messages:
        logger.debug("No older messages to summarize.")
        return messages

    older_conversation = "\n".join(f"{msg['role']}: {msg.get('content', '')}" for msg in older_messages)
    summary_prompt = [
        {"role": "system", "content": "You are a concise summarizer. Summarize the following conversation into a brief paragraph, focusing on key points and intent."},
        {"role": "user", "content": older_conversation}
    ]

    try:
        summary_response = await swarm.client.chat.completions.create(
            model=model,
            messages=summary_prompt,
            max_tokens=150,
            temperature=0.5
        )
        summary = summary_response.choices[0].message.content.strip()
        logger.debug(f"Generated summary: {summary}")
    except Exception as e:
        logger.error(f"Failed to summarize older messages: {e}")
        summary = "Summary unavailable due to processing error."

    summarized_messages = system_messages + [{"role": "system", "content": f"Summary of prior conversation: {summary}"}] + recent_messages
    logger.debug(f"Summarized to {len(summarized_messages)} messages")
    return summarized_messages

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
    def __init__(self, client=None, config: Optional[dict] = None, debug: bool = False):
        self.model = os.getenv("DEFAULT_LLM", "default")
        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.config = config or {}
        self.debug = debug
        logger.debug(f"Initializing Swarm with model={self.model}, debug={debug}")

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
        """Merge static agent functions with tools discovered from MCP servers asynchronously."""
        static_functions = agent.functions or []  # Preserve static functions
        logger.debug(f"Initial static functions for '{agent.name}': {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in static_functions]}")
        
        if not agent.mcp_servers:
            logger.debug(f"Agent '{agent.name}' has no MCP servers assigned. Using static functions only.")
            return static_functions

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
                    provider = MCPToolProvider.get_instance(server_name, server_config, total_timeout, debug=self.debug)
                    tools = await provider.discover_tools(agent)
                    for tool in tools:
                        if not hasattr(tool, "requires_approval"):
                            tool.requires_approval = True
                    logger.debug(f"Discovered {len(tools)} tools from '{server_name}': {[t.name for t in tools if hasattr(t, 'name')]}")
                    return tools
                except Exception as e:
                    logger.error(f"Failed to discover tools from '{server_name}': {e}")
                    return []

        logger.debug(f"Starting tool discovery tasks for {len(agent.mcp_servers)} servers")
        tasks = [discover_tools_from_server(server_name) for server_name in agent.mcp_servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Tool discovery tasks completed")

        discovered_tools = []
        for result in results:
            if isinstance(result, list):
                discovered_tools.extend(result)

        # Merge static and discovered tools, ensuring static functions persist
        all_functions = static_functions.copy()  # Start with static functions
        func_names = {getattr(f, "name", getattr(f, "__name__", "unnamed")) for f in all_functions}
        for tool in discovered_tools:
            name = getattr(tool, "name", getattr(tool, "__name__", "unnamed"))
            if name not in func_names:
                all_functions.append(tool)
                func_names.add(name)
            else:
                logger.debug(f"Skipping duplicate tool '{name}' during merge.")

        agent.functions = all_functions
        logger.debug(f"Total functions for '{agent.name}': {len(all_functions)} (Static: {len(static_functions)}, Discovered: {len(discovered_tools)})")
        logger.debug(f"Static: {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in static_functions]}")
        logger.debug(f"Discovered: {[t.name for t in discovered_tools if hasattr(t, 'name')]}")
        logger.debug(f"Combined functions for '{agent.name}': {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in all_functions]}")
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
        logger.debug(f"Entering get_chat_completion for agent '{agent.name}'")
        
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

        # Include all functions, using name or __name__
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
            if "context length" in str(e).lower():
                logger.warning(f"Context length exceeded: {e}. Truncating and retrying...")
                messages = truncate_message_history(messages, active_model, int(self.max_context_tokens * 0.75))
                create_params["messages"] = messages
                try:
                    completion = await self.client.chat.completions.create(**create_params)
                    logger.debug(f"OpenAI retry completion received for '{agent.name}'")
                    return completion.choices[0].message
                except OpenAIError as retry_e:
                    logger.error(f"Retry failed after truncation: {retry_e}")
                    raise
            else:
                logger.error(f"Chat completion failed: {e}")
                raise

    async def get_chat_completion_message(self, **kwargs) -> ChatCompletionMessage:
        """Extract the chat completion message asynchronously."""
        logger.debug("Entering get_chat_completion_message")
        completion = await self.get_chat_completion(**kwargs)
        logger.debug("Chat completion message extracted")
        if isinstance(completion, ChatCompletionMessage):
            return completion
        logger.debug(f"Unexpected completion type: {type(completion)}. Treating as message: {completion}")
        return ChatMessage(content=str(completion))

    def handle_function_result(self, result: Any, debug: bool) -> Result:
        """Convert function results into a standardized Result object."""
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
        """Handle tool calls asynchronously, executing functions and updating context."""
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
                if getattr(func, "dynamic", False):
                    logger.debug(f"Executing dynamic tool '{name}'")
                    raw_result = await func(**args)
                else:
                    logger.debug(f"Executing static tool '{name}'")
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
        """Run the swarm with streaming output, handling agent transitions and post-tool LLM responses."""
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
                
                # After tool execution, generate an LLM response
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
        """Run the swarm asynchronously, returning a response with post-tool LLM follow-up."""
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
                
                # After tool execution, generate an LLM response
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
        """Validate and filter message sequence for consistency."""
        logger.debug("Entering validate_message_sequence")
        valid_tool_call_ids = {tc["id"] for msg in messages if msg["role"] == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}
        return [msg for msg in messages if msg["role"] != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """Repair message payload by deduplicating, reordering, and ensuring tool call responses."""
        logger.debug(f"Entering repair_message_payload with {len(messages)} messages")
        messages = filter_duplicate_system_messages(messages)
        valid_tool_call_ids = {tc["id"] for msg in messages if msg["role"] == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"]}

        # Keep all messages initially
        repaired = messages.copy()

        final_sequence = []
        i = 0
        while i < len(repaired):
            msg = repaired[i]
            if msg["role"] == "assistant" and "tool_calls" in msg:
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                final_sequence.append(msg)
                j = i + 1
                tool_msgs = []
                found_ids = set()
                # Collect all tool messages that match any tool_call_id
                while j < len(repaired):
                    if repaired[j]["role"] == "tool" and repaired[j].get("tool_call_id") in tool_call_ids:
                        tool_msgs.append(repaired[j])
                        found_ids.add(repaired[j]["tool_call_id"])
                    j += 1
                final_sequence.extend(tool_msgs)
                # Add placeholder responses for missing tool calls
                missing_ids = tool_call_ids - found_ids
                for missing_id in missing_ids:
                    final_sequence.append({
                        "role": "tool",
                        "tool_call_id": missing_id,
                        "tool_name": "unknown",
                        "content": "Tool response pending or unavailable"
                    })
                    logger.debug(f"Added placeholder for missing tool_call_id: {missing_id}")
            else:
                final_sequence.append(msg)
            i += 1

        if debug:
            logger.debug(f"Repaired payload: {json.dumps(final_sequence, indent=2, default=str)}")
        return final_sequence
