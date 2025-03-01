"""
Swarm Core Module

Handles the initialization of the Swarm, agent management, and orchestration
of conversations between agents and MCP servers.
"""

# Standard library imports
import os
import copy
import datetime
import inspect
import json
import logging
import uuid
from collections import defaultdict
from typing import List, Optional, Dict, Any
from types import SimpleNamespace
from nemoguardrails.rails.llm.options import GenerationOptions

# Package/library imports
import asyncio
from openai import OpenAI

# Local imports
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

__CTX_VARS_NAME__ = "context_variables"

# Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
stream_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(stream_handler)


def serialize_datetime(obj):
    """Convert datetime objects to ISO format for JSON serialization."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not serializable")


def filter_duplicate_system_messages(messages):
    """
    Ensures only one system message exists in the conversation history.
    Prioritizes the system message assigned by the agent configuration.
    """
    filtered_messages = []
    system_message_found = False  # Track if we've already added a system message

    for message in messages:
        if message["role"] == "system":
            if system_message_found:
                continue  # Skip additional system messages
            system_message_found = True  # Mark that we've added one system message
        filtered_messages.append(message)

    return filtered_messages


def filter_messages(messages):
    """
    Filter messages to exclude those with null content
    """
    filtered_messages = []
    for message in messages:
        if message.get('content') is not None:
            filtered_messages.append(message)
    return filtered_messages


def update_null_content(messages):
    """
    Update messages with null content to an empty string.
    """
    for message in messages:
        if message.get('content') is None:
            message['content'] = ""
    return messages


def truncate_message_history(messages: List[dict], model: str, max_tokens: Optional[int] = None) -> List[dict]:
    """
    Truncates the conversation message history to ensure the total token count does not exceed the maximum context size.
    """
    import tiktoken
    from typing import List, Optional
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    if max_tokens is None:
        env_max = os.getenv("MAX_OUTPUT")
        if env_max:
            max_tokens = int(env_max)
        else:
            max_tokens = 2048

    total_tokens = sum(len(encoding.encode(msg.get("content", ""))) for msg in messages)
    while total_tokens > max_tokens and messages:
        removed = messages.pop(0)
        total_tokens -= len(encoding.encode(removed.get("content", "")))
    return messages


class ChatMessage(SimpleNamespace):
    def __init__(self, **kwargs):
        defaults = {
            "role": "assistant",
            "content": "",
            "sender": "assistant",
            "function_call": kwargs.get("function_call", None),
            "tool_calls": kwargs.get("tool_calls", [])
        }
        for key, default in defaults.items():
            if key not in kwargs or kwargs[key] is None:
                kwargs[key] = default
        super().__init__(**kwargs)

    def model_dump_json(self):
        d = self.__dict__.copy()
        if "tool_calls" in d and not d["tool_calls"]:
            del d["tool_calls"]
        return json.dumps(d)


class Swarm:
    def __init__(self, client=None, config: Optional[dict] = None):
        """
        Initialize the Swarm with an optional custom OpenAI client and preloaded configuration.
        """
        self.model = os.getenv("DEFAULT_LLM", "default")
        logger.debug(f"Initialized Swarm with model: {self.model}")

        self.temperature = 0.7
        self.tool_choice = "auto"
        self.parallel_tool_calls = False
        self.agents: Dict[str, Agent] = {}
        self.mcp_tool_providers: Dict[str, MCPToolProvider] = {}
        self.config = config or {}
        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
        except ValueError:
            logger.warning(f"LLM config for model '{self.model}' not found. Falling back to 'default'.")
            self.current_llm_config = load_llm_config(self.config, "default")

        if not self.current_llm_config.get("api_key"):
            if not os.getenv("SUPPRESS_DUMMY_KEY"):
                self.current_llm_config["api_key"] = "sk-DUMMYKEY"
            else:
                logger.debug("SUPPRESS_DUMMY_KEY is set; leaving API key empty.")

        if not client:
            client_kwargs = {}
            if "api_key" in self.current_llm_config:
                client_kwargs["api_key"] = self.current_llm_config["api_key"]
            if "base_url" in self.current_llm_config:
                client_kwargs["base_url"] = self.current_llm_config["base_url"]

            redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
            logger.debug(f"Initializing OpenAI client with kwargs: {redacted_kwargs}")

            client = OpenAI(**client_kwargs)
        self.client = client

        logger.info("Swarm initialized successfully.")

    def register_agent_functions_with_nemo(self, agent: Agent) -> None:
        """
        Registers the agent's functions as actions with the runtime for NeMo Guardrails.
        """
        if not getattr(agent, "nemo_guardrails_instance", None):
            if getattr(agent, "nemo_guardrails_config", None):
                config_path = f"nemo_guardrails/{agent.nemo_guardrails_config}/config.yml"
                try:
                    from nemoguardrails.guardrails import Guardrails
                    agent.nemo_guardrails_instance = Guardrails.from_yaml(config_path)
                    logger.debug("Initialized NeMo Guardrails instance from config.")
                except Exception as e:
                    logger.error(f"Error initializing NeMo Guardrails instance: {e}")
                    return
            else:
                logger.debug("No NeMo Guardrails instance or config for agent, skipping function registration.")
                return
        if not agent.functions:
            logger.debug("Agent has no functions to register.")
            return
        for func in agent.functions:
            action_name = getattr(func, '__name__', None) or getattr(func, '__qualname__', None)
            if not action_name:
                logger.warning("Skipping function registration: function has no name attribute")
                continue
            try:
                agent.nemo_guardrails_instance.runtime.register_action(func, name=action_name)
                logger.debug(f"Successfully registered function '{action_name}' as action.")
            except Exception as e:
                logger.error(f"Error registering function '{action_name}': {e}")

    async def discover_and_merge_agent_tools(self, agent: Agent, debug: bool = False) -> List[AgentFunction]:
        """
        Discover and merge tools for the given agent from assigned MCP servers in parallel using MCPToolProvider.

        Args:
            agent (Agent): The agent for which to discover and merge tools.
            debug (bool): Whether to enable additional debug logging.

        Returns:
            List[AgentFunction]: Combined list of agent's existing functions and newly discovered tools.
        """
        if not agent.mcp_servers:
            logger.debug(f"Agent '{agent.name}' has no assigned MCP servers.")
            return agent.functions

        # Base timeout of 10 seconds, scaled by number of MCP servers
        base_timeout = 10
        total_timeout = base_timeout * len(agent.mcp_servers)
        logger.debug(f"Setting discovery timeout to {total_timeout} seconds for {len(agent.mcp_servers)} MCP servers.")

        async def discover_tools_from_server(server_name):
            logger.debug(f"Looking up MCP server '{server_name}' for agent '{agent.name}'.")
            server_config = self.config.get("mcpServers", {}).get(server_name)
            if not server_config:
                logger.warning(f"MCP server '{server_name}' not found in configuration.")
                return []

            if server_name not in self.mcp_tool_providers:
                try:
                    # Pass the scaled timeout to MCPToolProvider
                    tool_provider = MCPToolProvider(server_name, server_config, timeout=total_timeout)
                    self.mcp_tool_providers[server_name] = tool_provider
                    logger.debug(f"Initialized MCPToolProvider for server '{server_name}' with timeout {total_timeout}s.")
                except Exception as e:
                    logger.error(f"Failed to initialize MCPToolProvider for server '{server_name}': {e}")
                    return []
            else:
                tool_provider = self.mcp_tool_providers[server_name]
                logger.debug(f"Using cached MCPToolProvider for server '{server_name}'.")

            try:
                tools = await tool_provider.discover_tools(agent)
                if tools:
                    logger.debug(f"Discovered {len(tools)} tools from server '{server_name}': {[tool.name for tool in tools if hasattr(tool, 'name')]}")
                else:
                    logger.debug(f"No tools discovered from server '{server_name}'.")
                return tools
            except Exception as e:
                logger.error(f"Error discovering tools from server '{server_name}': {e}")
                return []

        # Run discovery in parallel for all servers
        tasks = [discover_tools_from_server(server_name) for server_name in agent.mcp_servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, filtering out exceptions
        discovered_tools = []
        for result in results:
            if isinstance(result, list):
                discovered_tools.extend(result)
            else:
                logger.debug(f"Skipping result due to exception: {result}")

        all_functions = agent.functions + discovered_tools
        logger.debug(f"Total functions for agent '{agent.name}': {len(all_functions)} (Existing: {len(agent.functions)}, Discovered: {len(discovered_tools)})")
        if debug:
            logger.debug(f"[DEBUG] Existing functions: {[getattr(func, 'name', getattr(func, '__name__', 'unnamed')) for func in agent.functions]}")
            logger.debug(f"[DEBUG] Discovered tools: {[tool.name for tool in discovered_tools if hasattr(tool, 'name')]}")
            logger.debug(f"[DEBUG] Combined functions: {[getattr(func, 'name', getattr(func, '__name__', 'unnamed')) for func in all_functions]}")

        return all_functions

    def get_chat_completion(
        self,
        agent: Agent,
        history: List[Dict[str, Any]],
        context_variables: dict,
        model_override: Optional[str],
        stream: bool,
        debug: bool,
    ) -> ChatCompletionMessage:
        """Prepare and send a chat completion request to the OpenAI API."""
        new_llm_config = self.config.get("llm", {}).get(agent.model or "default")
        if new_llm_config is None:
            logger.warning(f"LLM config for model '{agent.model}' not found. Falling back to 'default'.")
            new_llm_config = self.config.get("llm", {}).get("default", {})

        if not new_llm_config.get("api_key"):
            if not os.getenv("SUPPRESS_DUMMY_KEY"):
                new_llm_config["api_key"] = "sk-DUMMYKEY"
            else:
                logger.debug("SUPPRESS_DUMMY_KEY is set; leaving API key empty.")

        old_llm_config = self.current_llm_config.copy() if self.current_llm_config else {}
        if not self.current_llm_config or \
           old_llm_config.get("base_url") != new_llm_config.get("base_url") or \
           old_llm_config.get("api_key") != new_llm_config.get("api_key"):
            client_kwargs = {}
            if "api_key" in new_llm_config:
                client_kwargs["api_key"] = new_llm_config["api_key"]
            if "base_url" in new_llm_config:
                client_kwargs["base_url"] = new_llm_config["base_url"]
            redacted_kwargs = redact_sensitive_data(client_kwargs, sensitive_keys=["api_key"])
            logger.debug(f"Reinitializing OpenAI client with kwargs: {redacted_kwargs}")
            self.client = OpenAI(**client_kwargs)
        self.current_llm_config = new_llm_config.copy()

        context_variables = defaultdict(str, context_variables)

        instructions = (agent.instructions(context_variables) if callable(agent.instructions) else agent.instructions)

        messages = [{"role": "system", "content": instructions}]

        seen_message_ids = set()
        for msg in history:
            msg_id = msg.get("id", hash(json.dumps(msg, sort_keys=True, default=serialize_datetime)))
            if msg_id in seen_message_ids:
                continue
            seen_message_ids.add(msg_id)
            messages.append(msg)

        messages = filter_duplicate_system_messages(messages)

        serialized_functions = [function_to_json(f) for f in agent.functions]
        tools = [func_dict for func_dict in serialized_functions]

        create_params = {
            "model": model_override or new_llm_config.get("model"),
            "messages": messages,
            "stream": stream,
        }

        if tools:
            create_params["tools"] = tools
            create_params["tool_choice"] = agent.tool_choice or "auto"

        if hasattr(agent, "response_format") and agent.response_format:
            create_params["response_format"] = agent.response_format

        if "temperature" in new_llm_config:
            create_params["temperature"] = new_llm_config["temperature"]

        if agent.response_format:
            create_params["response_format"] = agent.response_format

        try:
            logger.debug(f"[DEBUG] Chat completion payload: {json.dumps(create_params, indent=2, default=serialize_datetime)}")
        except Exception as e:
            logger.error(f"⚠️ Failed to serialize chat completion payload: {e}")

        try:
            if agent.nemo_guardrails_instance and messages[-1].get('content'):
                self.register_agent_functions_with_nemo(agent)
                options = GenerationOptions(
                    llm_params={"temperature": 0.5},
                    llm_output=True,
                    output_vars=True,
                    return_context=True
                )
                logger.debug(f"🔹 Using NeMo Guardrails for agent: {agent.name}")
                response = agent.nemo_guardrails_instance.generate(messages=update_null_content(messages), options=options)
                logger.debug(f"[DEBUG] Chat completion response: {response}")
                return response
            else:
                logger.debug(f"🔹 Using OpenAI Completion for agent: {agent.name}")
                return self.client.chat.completions.create(**json.loads(json.dumps(create_params, default=serialize_datetime)))
        except Exception as e:
            logger.debug(f"Error in chat completion request: {e}")
            raise

    def get_chat_completion_message(self, **kwargs):
        completion = self.get_chat_completion(**kwargs)
        logger.debug(f"Completion object: {completion}")
        if hasattr(completion, 'choices') and len(completion.choices) > 0:
            if hasattr(completion.choices[0], 'message'):
                return completion.choices[0].message
        logger.debug(f"Treating entire completion object as message: {completion}")
        return ChatMessage(content=json.dumps(completion.get("content")))

    def handle_function_result(self, result, debug) -> Result:
        """
        Process the result returned by an agent function.
        """
        match result:
            case Result() as result_obj:
                return result_obj
            case Agent() as agent:
                return Result(value=json.dumps({"assistant": agent.name}), agent=agent)
            case _:
                try:
                    return Result(value=str(result))
                except Exception as e:
                    error_message = f"Failed to cast response to string: {result}. Error: {str(e)}"
                    logger.debug(error_message)
                    raise TypeError(error_message)

    def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[AgentFunction],
        context_variables: dict,
        debug: bool,
    ) -> Response:
        """
        Handles tool calls, executing functions and processing results.
        """
        function_map = {}
        for f in functions:
            fname = getattr(f, "name", getattr(f, "__name__", None))
            if fname is None:
                logger.warning(f"Function {f} has no 'name' or '__name__' attribute; skipping.")
                continue
            function_map[fname] = f
        partial_response = Response(messages=[], agent=None, context_variables={})

        for tool_call in tool_calls:
            name = tool_call.function.name
            tool_call_id = tool_call.id

            if name not in function_map:
                error_msg = f"Tool {name} not found in function map."
                logger.error(error_msg)
                partial_response.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "tool_name": name,
                    "content": f"Error: {error_msg}",
                })
                continue

            func = function_map[name]
            args = json.loads(tool_call.function.arguments)

            if __CTX_VARS_NAME__ in func.__code__.co_varnames:
                args[__CTX_VARS_NAME__] = context_variables

            try:
                if getattr(func, "dynamic", False):
                    raw_result = asyncio.run(func(**args))
                else:
                    raw_result = func(**args)
                    if inspect.iscoroutine(raw_result):
                        logger.debug("Awaiting coroutine from static tool.")
                        raw_result = asyncio.run(raw_result)

                result = self.handle_function_result(raw_result, debug)
                partial_response.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "tool_name": name,
                    "content": json.dumps(result.value),
                })
                partial_response.context_variables.update(result.context_variables)

                if result.agent:
                    new_agent_name = result.agent.name
                    if new_agent_name and new_agent_name in self.agents:
                        partial_response.agent = result.agent
                        context_variables["active_agent_name"] = new_agent_name
                        logger.debug(f"🔄 Active agent updated to: {new_agent_name}")
                        new_agent = self.agents[new_agent_name]
                        new_agent.functions = asyncio.run(self.discover_and_merge_agent_tools(new_agent, debug=debug))
                        logger.debug(f"✅ Reloaded tools for new agent: {new_agent_name}")

            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                logger.error(error_msg)
                partial_response.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "tool_name": name,
                    "content": f"Error: {error_msg}",
                })

        return partial_response

    def run_and_stream(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ):
        """
        Generator to run the conversation with streaming responses.
        """
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        context_variables["active_agent_name"] = active_agent.name
        if debug:
            logger.debug(f"Initial active_agent_name set to: {active_agent.name}")

        all_functions = asyncio.run(self.discover_and_merge_agent_tools(agent, debug=debug))
        active_agent.functions = all_functions

        while len(history) - init_len < max_turns:
            message = {
                "content": "",
                "sender": active_agent.name,
                "role": "assistant",
                "function_call": None,
                "tool_calls": defaultdict(lambda: {"function": {"arguments": "", "name": ""}, "id": "", "type": ""}),
            }

            try:
                completion = self.get_chat_completion(
                    agent=active_agent,
                    history=history,
                    context_variables=context_variables,
                    model_override=model_override,
                    stream=True,
                    debug=debug,
                )
            except Exception as e:
                logger.error(f"Failed to get chat completion: {e}")
                if debug:
                    logger.debug(f"[DEBUG] Exception during get_chat_completion: {e}")
                break

            yield {"delim": "start"}
            for chunk in completion:
                try:
                    delta = chunk.choices[0].delta
                except Exception as e:
                    logger.debug(f"[ERROR] Failed to process chunk: {e}")
                    continue

                if delta.get("role") == "assistant":
                    message["role"] = "assistant"
                if "sender" not in message:
                    message["sender"] = active_agent.name
                yield delta

                merge_chunk(message, delta)
            yield {"delim": "end"}

            message["tool_calls"] = list(message.get("tool_calls", {}).values())
            if not message["tool_calls"]:
                message["tool_calls"] = None
            logger.debug(f"Received completion: {message}")
            history.append(message)

            if not message["tool_calls"] or not execute_tools:
                logger.debug("No tool calls or tool execution disabled. Ending turn.")
                break

            tool_calls = []
            for tool_call in message["tool_calls"]:
                function = Function(
                    arguments=tool_call["function"]["arguments"],
                    name=tool_call["function"]["name"],
                )
                tool_call_object = ChatCompletionMessageToolCall(
                    id=tool_call["id"],
                    function=function,
                    type=tool_call["type"]
                )
                tool_calls.append(tool_call_object)

            partial_response = self.handle_tool_calls(
                tool_calls, active_agent.functions, context_variables, debug
            )
            history.extend(partial_response.messages)
            context_variables.update(partial_response.context_variables)

            if partial_response.agent:
                active_agent = partial_response.agent
                context_variables["active_agent_name"] = active_agent.name
                if debug:
                    logger.debug(f"Active agent switched to: {active_agent.name}")

        yield {
            "response": Response(
                messages=history[init_len:],
                agent=active_agent,
                context_variables=context_variables,
            )
        }

    def run(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        stream: bool = False,
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        """
        Runs the conversation synchronously.
        """
        all_functions = asyncio.run(self.discover_and_merge_agent_tools(agent, debug=debug))
        agent.functions = all_functions
        if stream:
            return self.run_and_stream(
                agent=agent,
                messages=messages,
                context_variables=context_variables,
                model_override=model_override,
                debug=debug,
                max_turns=max_turns,
                execute_tools=execute_tools,
            )
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        context_variables["active_agent_name"] = active_agent.name

        turn_count = 0
        while turn_count < max_turns and active_agent:
            turn_count += 1

            try:
                message = self.get_chat_completion_message(
                    agent=active_agent,
                    history=history,
                    context_variables=context_variables,
                    model_override=model_override,
                    stream=stream,
                    debug=debug,
                )
            except Exception as e:
                logger.error(f"Failed to extract message from completion: {e}")
                break

            message.sender = active_agent.name

            raw_content = message.content or ""
            has_tool_calls = bool(message.tool_calls) or (message.function_call is not None)

            if debug:
                logger.debug(
                    f"[DEBUG] Received message from {message.sender}, raw_content={raw_content!r}, has_tool_calls={has_tool_calls}"
                )

            history.append(json.loads(message.model_dump_json()))

            if has_tool_calls and execute_tools:
                partial_response = self.handle_tool_calls(
                    message.tool_calls, active_agent.functions, context_variables, debug
                )
                history.extend(partial_response.messages)
                context_variables.update(partial_response.context_variables)

                if partial_response.agent:
                    active_agent = partial_response.agent
                    context_variables["active_agent_name"] = active_agent.name
                    logger.debug(f"Switched active agent to: {active_agent.name}")
                continue

            if raw_content.strip():
                break
            else:
                logger.debug("Empty assistant message with no tool calls. Ending.")
                break

        final_messages = history[init_len:]

        return Response(
            id=f"response-{uuid.uuid4()}",
            messages=final_messages,
            agent=active_agent,
            context_variables=context_variables,
        )

    def validate_message_sequence(self, messages):
        """
        Ensures the correct order of 'tool' messages in the conversation history.
        """
        valid_tool_call_ids = set()
        validated_messages = []

        for msg in messages:
            if msg["role"] == "assistant" and "tool_calls" in msg:
                for tool_call in msg["tool_calls"]:
                    valid_tool_call_ids.add(tool_call["id"])

            elif msg["role"] == "tool":
                if msg.get("tool_call_id") not in valid_tool_call_ids:
                    print(f"⚠️ WARNING: Orphaned tool message detected! Removing: {msg}")
                    continue
                valid_tool_call_ids.remove(msg["tool_call_id"])

            validated_messages.append(msg)

        return validated_messages

    def repair_message_payload(self, messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """
        Repairs the message sequence by ensuring every assistant message with tool_calls
        is followed by its corresponding tool messages, and removing orphaned tool messages.
        """
        filtered = []
        system_found = False
        for msg in messages:
            if msg["role"] == "system":
                if system_found:
                    continue
                system_found = True
            filtered.append(msg)
        messages = filtered

        valid_tool_call_ids = set()
        for msg in messages:
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id"):
                        valid_tool_call_ids.add(tc["id"])

        repaired = []
        for msg in messages:
            if msg["role"] == "tool":
                tc_id = msg.get("tool_call_id")
                if not tc_id or tc_id not in valid_tool_call_ids:
                    if debug:
                        logger.warning(f"Removing orphaned tool message: {msg}")
                    continue
                repaired.append(msg)
            else:
                repaired.append(msg)

        final_sequence: List[Dict[str, Any]] = []
        i = 0
        while i < len(repaired):
            msg = repaired[i]
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                tool_call_ids = [tc["id"] for tc in msg["tool_calls"] if "id" in tc]
                final_sequence.append(msg)
                j = i + 1
                to_remove_indexes = []
                found_tools_for_ids = []
                while j < len(repaired):
                    next_msg = repaired[j]
                    if next_msg["role"] == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                        found_tools_for_ids.append(next_msg)
                        to_remove_indexes.append(j)
                    j += 1
                for tmsg in found_tools_for_ids:
                    final_sequence.append(tmsg)
                for idx in reversed(to_remove_indexes):
                    repaired.pop(idx)
            else:
                final_sequence.append(msg)
            i += 1

        if debug:
            try:
                logger.debug("[DEBUG] Repaired message payload:\n" + json.dumps(final_sequence, indent=2, default=str))
            except Exception as e:
                logger.error(f"⚠️ Debug JSON serialization failed: {e}")

        return final_sequence
