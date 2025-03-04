# src/swarm/core.py
"""
Swarm Core Module

This module defines the Swarm class, which orchestrates the Swarm framework by managing agents,
tools, resources, and interactions with LLM endpoints and MCP servers. It supports asynchronous operations,
dynamic tool and resource discovery, and robust conversation handling.

Key Features:
- Initializes LLM clients with configurable settings.
- Discovers and merges static and MCP-provided tools and resources for agents.
- Handles chat completions and tool calls with error checking and logging.
- Provides streaming and non-streaming run modes for flexible agent interactions.
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

# Configure module-level logging for detailed diagnostics
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Constants for configuration and safety
__CTX_VARS_NAME__ = "context_variables"
GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("SWARM_MAX_CONTEXT_TOKENS", 8000))


class ChatMessage(SimpleNamespace):
    """
    A simplified structure for chat messages, ensuring compatibility with OpenAI's schema.

    Attributes:
        role (str): Role of the message sender (e.g., "assistant").
        content (str): Message content.
        sender (str): Custom field for sender identity (not sent to API).
        function_call (Optional[dict]): Deprecated function call data.
        tool_calls (Optional[List]): List of tool call objects or None.
    """

    def __init__(self, **kwargs):
        defaults = {
            "role": "assistant",
            "content": "",
            "sender": "assistant",
            "function_call": None,
            "tool_calls": None  # Changed to None for OpenAI schema compatibility
        }
        super().__init__(**(defaults | kwargs))
        # Guard: Ensure tool_calls is None or a valid list
        if self.tool_calls is not None and not isinstance(self.tool_calls, list):
            logger.warning(f"Invalid tool_calls type for sender '{self.sender}': {type(self.tool_calls)}. Resetting to None.")
            self.tool_calls = None
        elif self.tool_calls:
            # Convert to ChatCompletionMessageToolCall if necessary
            self.tool_calls = [tc if isinstance(tc, ChatCompletionMessageToolCall) else ChatCompletionMessageToolCall(**tc) for tc in self.tool_calls]
            logger.debug(f"Validated {len(self.tool_calls)} tool calls for sender '{self.sender}'")

    def model_dump_json(self) -> str:
        """Serialize the message to JSON, excluding custom fields and ensuring OpenAI compatibility."""
        d = {"role": self.role, "content": self.content}
        if hasattr(self, "function_call") and self.function_call is not None:
            d["function_call"] = self.function_call
        if hasattr(self, "tool_calls") and self.tool_calls is not None:
            d["tool_calls"] = [tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in self.tool_calls]
        serialized = json.dumps(d)
        if self.debug:
            logger.debug(f"Serialized message for '{self.sender}': {serialized}")
        return serialized


_discovery_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class Swarm:
    """
    Core class managing agent interactions within the Swarm framework.

    Responsibilities:
    - Initializes LLM clients with environment or config-provided credentials.
    - Manages agent registration, tool and resource discovery, and chat completions.
    - Supports synchronous and asynchronous operations with robust error handling.

    Attributes:
        model (str): Default LLM model identifier.
        temperature (float): Sampling temperature for LLM responses.
        tool_choice (str): Strategy for selecting tools (e.g., "auto").
        parallel_tool_calls (bool): Whether to execute tool calls in parallel.
        agents (Dict[str, Agent]): Registered agents by name.
        config (dict): Configuration for LLMs and MCP servers.
        debug (bool): Enable detailed logging if True.
        client (AsyncOpenAI): Client for interacting with OpenAI-compatible APIs.
    """

    def __init__(self, client: Optional[AsyncOpenAI] = None, config: Optional[Dict] = None, debug: bool = False):
        """
        Initialize the Swarm instance.

        Args:
            client: Optional pre-initialized AsyncOpenAI client.
            config: Configuration dictionary for LLMs and MCP servers.
            debug: Enable detailed logging if True.
        """
        self.model = os.getenv("DEFAULT_LLM", "default")
        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.config = config or {}
        self.debug = debug

        # Context limits with guards
        self.max_context_messages = 50
        self.max_context_tokens = max(1, GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS)  # Ensure positive
        self.summarize_threshold_tokens = int(self.max_context_tokens * 0.75)
        self.keep_recent_tokens = int(self.max_context_tokens * 0.25)
        logger.debug(f"Context limits set: max_messages={self.max_context_messages}, max_tokens={self.max_context_tokens}")

        # Load LLM configuration
        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
            if self.model == "default" and os.getenv("OPENAI_API_KEY"):
                self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                logger.debug(f"Overriding API key for model '{self.model}': {redact_sensitive_data(self.current_llm_config['api_key'])}")
        except ValueError as e:
            logger.warning(f"LLM config for '{self.model}' not found: {e}. Falling back to 'default'.")
            self.current_llm_config = load_llm_config(self.config, "default")
            if os.getenv("OPENAI_API_KEY"):
                self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                logger.debug(f"Overriding API key for fallback 'default': {redact_sensitive_data(self.current_llm_config['api_key'])}")

        # Fallback to dummy key if needed
        if not self.current_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            self.current_llm_config["api_key"] = "sk-DUMMYKEY"
            logger.debug("No API key provided—using dummy key 'sk-DUMMYKEY'")

        # Initialize AsyncOpenAI client
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(f"Initializing AsyncOpenAI client with model='{self.model}', base_url='{client_kwargs.get('base_url', 'default')}', api_key={redacted_kwargs['api_key']}")
        self.client = client or AsyncOpenAI(**client_kwargs)

        logger.info(f"Swarm initialized with max_context_tokens={self.max_context_tokens}")

    def register_agent_functions_with_nemo(self, agent: Agent) -> None:
        """
        Register agent functions with NeMo Guardrails if configured.

        Args:
            agent: The agent whose functions need registration.
        """
        if not agent:
            logger.error("Cannot register functions: Agent is None")
            return

        if not getattr(agent, "nemo_guardrails_instance", None) and getattr(agent, "nemo_guardrails_config", None):
            config_path = f"nemo_guardrails/{agent.nemo_guardrails_config}/config.yml"
            try:
                from nemoguardrails.guardrails import Guardrails
                agent.nemo_guardrails_instance = Guardrails.from_yaml(config_path)
                logger.debug(f"Initialized NeMo Guardrails for agent '{agent.name}'")
            except Exception as e:
                logger.error(f"Failed to initialize NeMo Guardrails for '{agent.name}': {e}")
                return

        if not agent.functions or not getattr(agent, "nemo_guardrails_instance", None):
            logger.debug(f"Skipping NeMo registration for '{agent.name}': No functions ({len(agent.functions)}) or no instance")
            return

        for func in agent.functions:
            action_name = getattr(func, '__name__', None) or getattr(func, '__qualname__', None)
            if not action_name:
                logger.warning(f"Skipping function registration for '{agent.name}': No name attribute")
                continue
            try:
                agent.nemo_guardrails_instance.runtime.register_action(func, name=action_name)
                logger.debug(f"Registered function '{action_name}' with NeMo Guardrails for '{agent.name}'")
            except Exception as e:
                logger.error(f"Failed to register function '{action_name}' for '{agent.name}': {e}")

    async def discover_and_merge_agent_tools(self, agent: Agent, debug: bool = False) -> List[AgentFunction]:
        """
        Discover tools from MCP servers and merge with agent's static functions, deduplicating MCP tools.

        Args:
            agent: The agent for which to discover tools.
            debug: If True, log detailed debugging information.

        Returns:
            List[AgentFunction]: Combined list of static and unique MCP-discovered tools.
        """
        if not agent:
            logger.error("Cannot discover tools: Agent is None")
            return []

        logger.debug(f"Discovering tools for agent '{agent.name}'")
        if not agent.mcp_servers:
            funcs = agent.functions or []
            logger.debug(f"Agent '{agent.name}' has no MCP servers. Returning static functions: {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in funcs]}")
            return funcs

        discovered_tools = []
        for server_name in agent.mcp_servers:
            if not isinstance(server_name, str):
                logger.warning(f"Invalid server name type for '{agent.name}': {type(server_name)}. Skipping.")
                continue
            logger.debug(f"Discovering tools from MCP server '{server_name}' for '{agent.name}'")
            server_config = self.config.get("mcpServers", {}).get(server_name, {})
            if not server_config:
                logger.warning(f"MCP server '{server_name}' not found in config for '{agent.name}'")
                continue
            try:
                provider = MCPToolProvider.get_instance(server_name, server_config, timeout=15, debug=debug)
                tools = await provider.discover_tools(agent)
                if not isinstance(tools, list):
                    logger.warning(f"Invalid tools format from '{server_name}' for '{agent.name}': {type(tools)}. Expected list.")
                    continue
                for tool in tools:
                    if not hasattr(tool, "requires_approval"):
                        tool.requires_approval = True
                discovered_tools.extend(tools)
                logger.debug(f"Discovered {len(tools)} tools from '{server_name}': {[getattr(t, 'name', 'unnamed') for t in tools]}")
            except Exception as e:
                logger.error(f"Failed to discover tools from '{server_name}' for '{agent.name}': {e}")

        # Deduplicate MCP tools by name, preserving static functions
        unique_discovered_tools = list(dict.fromkeys(discovered_tools))
        all_functions = (agent.functions or []) + unique_discovered_tools

        if debug:
            static_names = [getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in (agent.functions or [])]
            discovered_names = [getattr(t, 'name', 'unnamed') for t in discovered_tools]
            unique_discovered_names = [getattr(t, 'name', 'unnamed') for t in unique_discovered_tools]
            combined_names = [getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in all_functions]
            logger.debug(f"[DEBUG] Static functions for '{agent.name}': {static_names}")
            logger.debug(f"[DEBUG] Discovered tools (before dedup) for '{agent.name}': {discovered_names}")
            logger.debug(f"[DEBUG] Discovered tools (after dedup) for '{agent.name}': {unique_discovered_names}")
            logger.debug(f"[DEBUG] Combined functions for '{agent.name}': {combined_names}")
        logger.debug(f"Total functions for '{agent.name}': {len(all_functions)} (Static: {len(agent.functions or [])}, Discovered: {len(unique_discovered_tools)})")
        return all_functions

    async def discover_and_merge_agent_resources(self, agent: Agent, debug: bool = False) -> List[Dict[str, Any]]:
        """
        Discover resources from MCP servers and merge with agent's static resources, deduplicating MCP resources by URI.

        Args:
            agent: The agent for which to discover resources.
            debug: If True, log detailed debugging information.

        Returns:
            List[Dict[str, Any]]: Combined list of static and unique MCP-discovered resources.
        """
        if not agent:
            logger.error("Cannot discover resources: Agent is None")
            return []

        logger.debug(f"Discovering resources for agent '{agent.name}'")
        if not agent.mcp_servers:
            resources = agent.resources or []
            logger.debug(f"Agent '{agent.name}' has no MCP servers. Returning static resources: {[r.get('name', 'unnamed') for r in resources]}")
            return resources

        discovered_resources = []
        for server_name in agent.mcp_servers:
            if not isinstance(server_name, str):
                logger.warning(f"Invalid server name type for '{agent.name}': {type(server_name)}. Skipping.")
                continue
            logger.debug(f"Discovering resources from MCP server '{server_name}' for '{agent.name}'")
            server_config = self.config.get("mcpServers", {}).get(server_name, {})
            if not server_config:
                logger.warning(f"MCP server '{server_name}' not found in config for '{agent.name}'")
                continue
            try:
                provider = MCPToolProvider.get_instance(server_name, server_config, timeout=15, debug=debug)
                # Fetch resources using list_resources from MCP client
                resources_response = await provider.client.list_resources()
                if not isinstance(resources_response, dict) or "resources" not in resources_response:
                    logger.warning(f"Invalid resources response from '{server_name}' for '{agent.name}': {resources_response}. Expected dict with 'resources' key.")
                    continue
                resources = resources_response["resources"]
                if not isinstance(resources, list):
                    logger.warning(f"Invalid resources format from '{server_name}' for '{agent.name}': {type(resources)}. Expected list.")
                    continue
                discovered_resources.extend(resources)
                logger.debug(f"Discovered {len(resources)} resources from '{server_name}': {[r.get('name', 'unnamed') for r in resources]}")
            except Exception as e:
                logger.error(f"Failed to discover resources from '{server_name}' for '{agent.name}': {e}")

        # Deduplicate MCP resources by 'uri', preserving static resources
        unique_discovered_resources = list({r['uri']: r for r in discovered_resources if 'uri' in r}.values())
        all_resources = (agent.resources or []) + unique_discovered_resources

        if debug:
            static_names = [r.get('name', 'unnamed') for r in (agent.resources or [])]
            discovered_names = [r.get('name', 'unnamed') for r in discovered_resources]
            unique_discovered_names = [r.get('name', 'unnamed') for r in unique_discovered_resources]
            combined_names = [r.get('name', 'unnamed') for r in all_resources]
            logger.debug(f"[DEBUG] Static resources for '{agent.name}': {static_names}")
            logger.debug(f"[DEBUG] Discovered resources (before dedup) for '{agent.name}': {discovered_names}")
            logger.debug(f"[DEBUG] Discovered resources (after dedup) for '{agent.name}': {unique_discovered_names}")
            logger.debug(f"[DEBUG] Combined resources for '{agent.name}': {combined_names}")
        logger.debug(f"Total resources for '{agent.name}': {len(all_resources)} (Static: {len(agent.resources or [])}, Discovered: {len(unique_discovered_resources)})")
        return all_resources

    async def get_chat_completion(
        self,
        agent: Agent,
        history: List[Dict[str, Any]],
        context_variables: dict,
        model_override: Optional[str] = None,
        stream: bool = False,
        debug: bool = False
    ) -> ChatCompletionMessage:
        """
        Retrieve a chat completion from the LLM for the given agent and history.

        Args:
            agent: The agent processing the completion.
            history: List of previous messages in the conversation.
            context_variables: Variables to include in the agent's context.
            model_override: Optional model to use instead of default.
            stream: If True, stream the response; otherwise, return complete.
            debug: If True, log detailed debugging information.

        Returns:
            ChatCompletionMessage: The LLM's response message.
        """
        if not agent:
            logger.error("Cannot generate chat completion: Agent is None")
            raise ValueError("Agent is required")

        logger.debug(f"Generating chat completion for agent '{agent.name}'")
        active_model = model_override or self.current_llm_config.get("model", self.model)
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
        logger.debug(f"Using client with model='{active_model}', base_url='{client_kwargs.get('base_url', 'default')}', api_key={redacted_kwargs['api_key']}")

        context_variables = defaultdict(str, context_variables)
        instructions = agent.instructions(context_variables) if callable(agent.instructions) else agent.instructions
        if not isinstance(instructions, str):
            logger.warning(f"Invalid instructions type for '{agent.name}': {type(instructions)}. Converting to string.")
            instructions = str(instructions)
        messages = [{"role": "system", "content": instructions}]

        if not isinstance(history, list):
            logger.error(f"Invalid history type for '{agent.name}': {type(history)}. Expected list.")
            history = []
        seen_ids = set()
        for msg in history:
            msg_id = msg.get("id", hash(json.dumps(msg, sort_keys=True, default=serialize_datetime)))
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                if "tool_calls" in msg and msg["tool_calls"] is not None and not isinstance(msg["tool_calls"], list):
                    logger.warning(f"Invalid tool_calls in history for '{msg.get('sender', 'unknown')}': {msg['tool_calls']}. Setting to None.")
                    msg["tool_calls"] = None
                messages.append(msg)
        messages = filter_duplicate_system_messages(messages)
        messages = truncate_message_history(messages, active_model, self.max_context_tokens, self.max_context_messages)

        tools = [function_to_json(f, truncate_desc=True) for f in agent.functions]
        logger.debug(f"Tools for '{agent.name}': {[getattr(f, 'name', getattr(f, '__name__', 'unnamed')) for f in agent.functions]}")
        if debug:
            logger.debug(f"Resources for '{agent.name}': {[r.get('name', 'unnamed') for r in agent.resources]}")

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
                    logger.debug(f"OpenAI completion received for '{agent.name}': {completion.choices[0].message.content[:50]}...")
                    return completion.choices[0].message
                finally:
                    if prev_openai_api_key is not None:
                        os.environ["OPENAI_API_KEY"] = prev_openai_api_key
        except OpenAIError as e:
            logger.error(f"Chat completion failed for '{agent.name}': {e}")
            raise

    async def get_chat_completion_message(self, **kwargs) -> ChatCompletionMessage:
        """Wrapper to retrieve and validate a chat completion message."""
        logger.debug("Fetching chat completion message")
        completion = await self.get_chat_completion(**kwargs)
        if isinstance(completion, ChatCompletionMessage):
            return completion
        logger.warning(f"Unexpected completion type: {type(completion)}. Converting to ChatMessage.")
        return ChatMessage(content=str(completion))

    def handle_function_result(self, result: Any, debug: bool) -> Result:
        """
        Process a tool call result into a standardized Result object.

        Args:
            result: The raw result from a tool call.
            debug: If True, log detailed result information.

        Returns:
            Result: Standardized result object.
        """
        logger.debug("Processing function result")
        if debug:
            logger.debug(f"Raw result type: {type(result)}, value: {str(result)[:100]}...")

        match result:
            case Result() as result_obj:
                return result_obj
            case Agent() as agent:
                logger.debug(f"Result is an Agent: '{agent.name}'")
                return Result(value=json.dumps({"assistant": agent.name}), agent=agent)
            case _:
                try:
                    result_str = str(result)
                    logger.debug(f"Converted result to string: {result_str[:50]}...")
                    return Result(value=result_str)
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
        """
        Execute tool calls and aggregate their results into a Response.

        Args:
            tool_calls: List of tool calls requested by the LLM.
            functions: Available agent functions to execute.
            context_variables: Variables to pass to tool calls.
            debug: If True, log detailed execution information.

        Returns:
            Response: Aggregated results of tool executions.
        """
        if not tool_calls or not isinstance(tool_calls, list):
            logger.debug("No valid tool calls provided")
            return Response(messages=[], agent=None, context_variables={})

        logger.debug(f"Handling {len(tool_calls)} tool calls")
        function_map = {getattr(f, "name", getattr(f, "__name__", "unnamed")): f for f in functions if getattr(f, "name", getattr(f, "__name__", None))}
        partial_response = Response(messages=[], agent=None, context_variables={})

        for tool_call in tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageToolCall):
                logger.warning(f"Invalid tool_call type: {type(tool_call)}. Skipping.")
                continue
            name = tool_call.function.name
            tool_call_id = tool_call.id

            if not name or not tool_call_id:
                logger.error(f"Invalid tool call: name={name}, id={tool_call_id}. Skipping.")
                continue

            if name not in function_map:
                logger.error(f"Tool '{name}' not found in function map for call ID '{tool_call_id}'")
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": f"Error: Tool {name} not found."
                })
                continue

            func = function_map[name]
            try:
                args = json.loads(tool_call.function.arguments)
                if not isinstance(args, dict):
                    logger.warning(f"Invalid arguments for '{name}': {args}. Using empty dict.")
                    args = {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse arguments for '{name}': {e}. Using empty dict.")
                args = {}

            if __CTX_VARS_NAME__ in func.__code__.co_varnames:
                args[__CTX_VARS_NAME__] = context_variables

            try:
                raw_result = func(**args)
                if inspect.isawaitable(raw_result):
                    logger.debug(f"Awaiting result for tool '{name}' with call ID '{tool_call_id}'")
                    raw_result = await raw_result
                else:
                    logger.debug(f"Executed sync tool '{name}' with call ID '{tool_call_id}'")

                result = self.handle_function_result(raw_result, debug)
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": json.dumps(result.value)
                })
                partial_response.context_variables.update(result.context_variables)
                if result.agent:
                    partial_response.agent = result.agent
                    context_variables["active_agent_name"] = result.agent.name
                    logger.debug(f"Switched to agent '{result.agent.name}' via tool '{name}'")
            except Exception as e:
                logger.error(f"Error executing tool '{name}' with call ID '{tool_call_id}': {e}")
                partial_response.messages.append({
                    "role": "tool", "tool_call_id": tool_call_id, "tool_name": name,
                    "content": f"Error: {str(e)}"
                })

        logger.debug(f"Processed {len(partial_response.messages)} tool call responses")
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
        """
        Run the swarm in streaming mode, yielding responses incrementally.

        Args:
            agent: The starting agent.
            messages: Initial conversation history.
            context_variables: Variables to include in the context.
            model_override: Optional model to override default.
            debug: If True, log detailed execution information.
            max_turns: Maximum number of turns to process.
            execute_tools: If True, execute tool calls.

        Yields:
            Dict: Streamed chunks or final response.
        """
        if not agent:
            logger.error("Cannot run in streaming mode: Agent is None")
            return

        logger.debug(f"Starting streaming run for agent '{agent.name}' with {len(messages)} messages")
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        if not isinstance(context_variables, dict):
            logger.warning(f"Invalid context_variables type: {type(context_variables)}. Using empty dict.")
            context_variables = {}
        context_variables["active_agent_name"] = active_agent.name

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
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected in turn {turn}")

                logger.debug(f"Generating response after tool calls for '{active_agent.name}' in turn {turn}")
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

        logger.debug(f"Streaming run completed with {len(history[init_len:])} new messages after {turn} turns")
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
        """
        Execute the swarm run in streaming or non-streaming mode.

        Args:
            agent: The starting agent.
            messages: Initial conversation history.
            context_variables: Variables to include in the context.
            model_override: Optional model to override default.
            stream: If True, return a streaming generator; otherwise, a single Response.
            debug: If True, log detailed execution information.
            max_turns: Maximum number of turns to process.
            execute_tools: If True, execute tool calls.

        Returns:
            Response: Final response object or generator if streaming.
        """
        if not agent:
            logger.error("Cannot run: Agent is None")
            raise ValueError("Agent is required")

        logger.debug(f"Starting run for agent '{agent.name}' with {len(messages)} messages, stream={stream}")
        if stream:
            return self.run_and_stream(
                agent=agent, messages=messages, context_variables=context_variables,
                model_override=model_override, debug=debug, max_turns=max_turns, execute_tools=execute_tools
            )

        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        if not isinstance(context_variables, dict):
            logger.warning(f"Invalid context_variables type: {type(context_variables)}. Using empty dict.")
            context_variables = {}
        context_variables["active_agent_name"] = active_agent.name

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
                    logger.debug(f"Agent handoff to '{active_agent.name}' detected in turn {turn}")

                logger.debug(f"Generating response after tool calls for '{active_agent.name}' in turn {turn}")
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

        logger.debug(f"Run completed with {len(history[init_len:])} new messages after {turn} turns")
        response = Response(id=f"response-{uuid.uuid4()}", messages=history[init_len:], agent=active_agent, context_variables=context_variables)
        if debug:
            logger.debug(f"Response ID: {response.id}, messages count: {len(response.messages)}")
        return response

    def validate_message_sequence(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure tool messages correspond to valid tool calls in the sequence.

        Args:
            messages: List of messages to validate.

        Returns:
            List[Dict[str, Any]]: Validated and filtered message sequence.
        """
        if not isinstance(messages, list):
            logger.error(f"Invalid messages type for validation: {type(messages)}. Returning empty list.")
            return []

        logger.debug(f"Validating message sequence with {len(messages)} messages")
        valid_tool_call_ids = {tc["id"] for msg in messages if msg.get("role") == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"] if isinstance(tc, dict) and "id" in tc}
        return [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """
        Repair the message sequence by reordering tool messages after their corresponding calls.

        Args:
            messages: List of messages to repair.
            debug: If True, log detailed repair information.

        Returns:
            List[Dict[str, Any]]: Repaired message sequence.
        """
        if not isinstance(messages, list):
            logger.error(f"Invalid messages type for repair: {type(messages)}. Returning empty list.")
            return []

        logger.debug(f"Repairing message payload with {len(messages)} messages")
        messages = filter_duplicate_system_messages(messages)
        valid_tool_call_ids = {tc["id"] for msg in messages if msg.get("role") == "assistant" and "tool_calls" in msg for tc in msg["tool_calls"] if isinstance(tc, dict) and "id" in tc}
        repaired = [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]
        final_sequence = []
        i = 0
        while i < len(repaired):
            msg = repaired[i]
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                tool_call_ids = [tc["id"] for tc in msg["tool_calls"] if isinstance(tc, dict) and "id" in tc]
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