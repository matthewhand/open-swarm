"""
Swarm Core Module

This module defines the Swarm class, which orchestrates the Swarm framework by managing agents
and coordinating interactions with LLM endpoints and MCP servers. Modularized components live
in separate files for clarity.
"""

import os
import copy
import json
import logging
import uuid
from typing import List, Optional, Dict, Any
from types import SimpleNamespace # Needed for stream processing

import asyncio
from openai import AsyncOpenAI

# Internal imports for modular components
from .util import merge_chunk
from .types import Agent, Response, ChatCompletionMessageToolCall # Ensure necessary types are imported
from .extensions.config.config_loader import load_llm_config
# Use mcp_utils from the extensions directory
from .extensions.mcp.mcp_utils import discover_and_merge_agent_tools, discover_and_merge_agent_resources
from .settings import DEBUG
from .utils.redact import redact_sensitive_data
# Import chat completion logic
from .llm.chat_completion import get_chat_completion, get_chat_completion_message
# Import message and tool execution logic
from .messages import ChatMessage
from .tool_executor import handle_tool_calls

# Configure module-level logging
logger = logging.getLogger(__name__)
# Set level based on DEBUG setting or default to INFO
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
# Ensure handler is added only once
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Constants
__CTX_VARS_NAME__ = "context_variables" # Standard name for context injection
GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("SWARM_MAX_CONTEXT_TOKENS", 8000)) # Default from env

_discovery_locks: Dict[str, asyncio.Lock] = {} # Lock for async discovery


class Swarm:
    """
    Core class managing agent interactions within the Swarm framework.

    Attributes:
        model (str): Default LLM model identifier.
        temperature (float): Sampling temperature for LLM responses.
        tool_choice (str): Strategy for selecting tools (e.g., "auto").
        parallel_tool_calls (bool): Whether to execute tool calls in parallel.
        agents (Dict[str, Agent]): Registered agents by name.
        config (dict): Configuration for LLMs and MCP servers.
        debug (bool): Enable detailed logging if True.
        client (AsyncOpenAI): Client for OpenAI-compatible APIs.
        current_llm_config (dict): Loaded config for the current default LLM.
        max_context_messages (int): Max messages to keep in history.
        max_context_tokens (int): Max tokens allowed in history.
    """

    def __init__(self, client: Optional[AsyncOpenAI] = None, config: Optional[Dict] = None, debug: bool = False):
        """
        Initialize the Swarm instance.

        Args:
            client: Optional pre-initialized AsyncOpenAI client.
            config: Configuration dictionary for LLMs and MCP servers.
            debug: Enable detailed logging if True.
        """
        self.model = os.getenv("DEFAULT_LLM", "default") # Default LLM profile name
        self.temperature = 0.7 # Default temperature
        self.tool_choice = "auto" # Default tool choice strategy
        self.parallel_tool_calls = False # Default parallel tool call setting
        self.agents: Dict[str, Agent] = {} # Dictionary to store registered agents
        self.config = config or {} # Store provided or empty config
        self.debug = debug or DEBUG # Use provided debug flag or global setting

        # Context limits
        self.max_context_messages = 50 # Default max messages
        self.max_context_tokens = max(1, GLOBAL_DEFAULT_MAX_CONTEXT_TOKENS) # Ensure positive token limit
        # Derived limits (optional, consider moving logic to truncation function)
        # self.summarize_threshold_tokens = int(self.max_context_tokens * 0.75)
        # self.keep_recent_tokens = int(self.max_context_tokens * 0.25)
        logger.debug(f"Context limits set: max_messages={self.max_context_messages}, max_tokens={self.max_context_tokens}")

        # Load LLM configuration for the default model
        try:
            self.current_llm_config = load_llm_config(self.config, self.model)
            # Override API key from environment if using 'default' profile and key exists
            if self.model == "default" and os.getenv("OPENAI_API_KEY"):
                self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                logger.debug(f"Overriding API key for model '{self.model}' from OPENAI_API_KEY env var.")
        except ValueError as e:
            logger.warning(f"LLM config for '{self.model}' not found: {e}. Falling back to loading 'default' profile.")
            # Attempt to load the 'default' profile explicitly as fallback
            try:
                 self.current_llm_config = load_llm_config(self.config, "default")
                 if os.getenv("OPENAI_API_KEY"): # Also check env var for fallback default
                      self.current_llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
                      logger.debug("Overriding API key for fallback 'default' profile from OPENAI_API_KEY env var.")
            except ValueError as e_default:
                 logger.error(f"Fallback 'default' LLM profile also not found: {e_default}. Swarm may not function correctly.")
                 self.current_llm_config = {} # Set empty config to avoid downstream errors

        # Provide a dummy key if no real key is found and suppression is off
        if not self.current_llm_config.get("api_key") and not os.getenv("SUPPRESS_DUMMY_KEY"):
            self.current_llm_config["api_key"] = "sk-DUMMYKEY" # Use dummy key
            logger.debug("No API key provided or found—using dummy key 'sk-DUMMYKEY'")

        # Initialize AsyncOpenAI client using loaded config
        # Filter out None values before passing to AsyncOpenAI constructor
        client_kwargs = {
            "api_key": self.current_llm_config.get("api_key"),
            "base_url": self.current_llm_config.get("base_url")
        }
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}

        # Log client initialization details (redacting API key)
        redacted_kwargs_log = client_kwargs.copy()
        if 'api_key' in redacted_kwargs_log:
             redacted_kwargs_log['api_key'] = redact_sensitive_data(redacted_kwargs_log['api_key'])
        logger.debug(f"Initializing AsyncOpenAI client with kwargs: {redacted_kwargs_log}")

        # Use provided client or create a new one
        self.client = client or AsyncOpenAI(**client_kwargs)

        logger.info(f"Swarm initialized. Default LLM: '{self.model}', Max Tokens: {self.max_context_tokens}")

    async def run_and_stream(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        debug: bool = False,
        max_turns: int = float("inf"), # Allow infinite turns by default
        execute_tools: bool = True
    ):
        """
        Run the swarm in streaming mode, yielding responses incrementally.

        Args:
            agent: Starting agent.
            messages: Initial conversation history.
            context_variables: Variables to include in the context.
            model_override: Optional model to override default.
            debug: If True, log detailed execution information.
            max_turns: Maximum number of agent turns to process.
            execute_tools: If True, execute tool calls requested by the agent.

        Yields:
            Dict: Streamed chunks (OpenAI format delta) or final response structure.
        """
        if not agent:
            logger.error("Cannot run in streaming mode: Agent is None")
            yield {"error": "Agent is None"} # Yield an error structure
            return

        effective_debug = debug or self.debug # Use local debug flag or instance default
        logger.debug(f"Starting streaming run for agent '{agent.name}' with {len(messages)} messages")

        active_agent = agent
        # Deep copy context and history to avoid modifying originals
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages) # Store initial length to return only new messages

        # Ensure context_variables is a dict and set active agent name
        if not isinstance(context_variables, dict):
            logger.warning(f"Invalid context_variables type: {type(context_variables)}. Using empty dict.")
            context_variables = {}
        context_variables["active_agent_name"] = active_agent.name

        # Discover tools and resources for the initial agent if not already done
        # Use flags to avoid repeated discovery within the same run instance
        if not hasattr(active_agent, '_tools_discovered'):
             active_agent.functions = await discover_and_merge_agent_tools(active_agent, self.config, effective_debug)
             active_agent._tools_discovered = True
        if not hasattr(active_agent, '_resources_discovered'):
            active_agent.resources = await discover_and_merge_agent_resources(active_agent, self.config, effective_debug)
            active_agent._resources_discovered = True


        turn = 0
        while turn < max_turns:
            turn += 1
            logger.debug(f"Turn {turn} starting with agent '{active_agent.name}'.")
            # Prepare message object for accumulating response
            message = ChatMessage(sender=active_agent.name)

            # Get chat completion stream
            completion_stream = await get_chat_completion(
                self.client, active_agent, history, context_variables, self.current_llm_config,
                self.max_context_tokens, self.max_context_messages, model_override, stream=True, debug=effective_debug
            )

            yield {"delim": "start"} # Signal start of response stream
            current_tool_calls_data = [] # Accumulate tool call data from chunks
            async for chunk in completion_stream:
                if not chunk.choices: continue # Skip empty chunks
                delta = chunk.choices[0].delta
                # Update message object with content from the chunk
                merge_chunk(message, delta)
                # Accumulate tool call chunks
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        # Find or create tool call entry in accumulator
                        found = False
                        for existing_tc_data in current_tool_calls_data:
                            if existing_tc_data['index'] == tc_chunk.index:
                                # Merge chunk into existing tool call data
                                if tc_chunk.id: existing_tc_data['id'] = existing_tc_data.get('id', "") + tc_chunk.id
                                if tc_chunk.type: existing_tc_data['type'] = tc_chunk.type
                                if tc_chunk.function:
                                    if 'function' not in existing_tc_data: existing_tc_data['function'] = {'name': "", 'arguments': ""}
                                    func_data = existing_tc_data['function']
                                    if tc_chunk.function.name: func_data['name'] = func_data.get('name', "") + tc_chunk.function.name
                                    if tc_chunk.function.arguments: func_data['arguments'] = func_data.get('arguments', "") + tc_chunk.function.arguments
                                found = True
                                break
                        if not found:
                            # Add new tool call data initialized from chunk
                            new_tc_data = {'index': tc_chunk.index}
                            if tc_chunk.id: new_tc_data['id'] = tc_chunk.id
                            if tc_chunk.type: new_tc_data['type'] = tc_chunk.type
                            if tc_chunk.function:
                                 new_tc_data['function'] = {}
                                 if tc_chunk.function.name: new_tc_data['function']['name'] = tc_chunk.function.name
                                 if tc_chunk.function.arguments: new_tc_data['function']['arguments'] = tc_chunk.function.arguments
                            current_tool_calls_data.append(new_tc_data)

                yield delta # Yield the raw chunk
            yield {"delim": "end"} # Signal end of response stream

            # Finalize tool calls for the completed message from accumulated data
            if current_tool_calls_data:
                 message.tool_calls = [
                      ChatCompletionMessageToolCall(**tc_data) # Instantiate objects from data
                      for tc_data in current_tool_calls_data
                      # Ensure essential keys are present before instantiation
                      if 'id' in tc_data and 'type' in tc_data and 'function' in tc_data
                 ]
            else:
                 message.tool_calls = None

            # Add the fully formed assistant message (potentially with tool calls) to history
            history.append(json.loads(message.model_dump_json()))

            # --- Tool Execution Phase ---
            if message.tool_calls and execute_tools:
                logger.debug(f"Turn {turn}: Agent '{active_agent.name}' requested {len(message.tool_calls)} tool calls.")
                # Execute tools
                partial_response = await handle_tool_calls(message.tool_calls, active_agent.functions, context_variables, effective_debug)
                # Add tool results to history
                history.extend(partial_response.messages)
                # Update context variables from tool results
                context_variables.update(partial_response.context_variables)

                # Check for agent handoff
                if partial_response.agent and partial_response.agent != active_agent:
                    active_agent = partial_response.agent
                    context_variables["active_agent_name"] = active_agent.name # Update context
                    logger.debug(f"Turn {turn}: Agent handoff to '{active_agent.name}' detected via tool call.")
                    # Discover tools/resources for the new agent if needed
                    if not hasattr(active_agent, '_tools_discovered'):
                        active_agent.functions = await discover_and_merge_agent_tools(active_agent, self.config, effective_debug)
                        active_agent._tools_discovered = True
                    if not hasattr(active_agent, '_resources_discovered'):
                        active_agent.resources = await discover_and_merge_agent_resources(active_agent, self.config, effective_debug)
                        active_agent._resources_discovered = True

                # Continue the loop to get the next response from the (potentially new) agent
                logger.debug(f"Turn {turn}: Continuing loop after tool execution.")
                continue # Go to the start of the while loop for the next turn

            else: # If no tool calls requested or execute_tools is False
                logger.debug(f"Turn {turn}: No tool calls requested or execution disabled. Ending run.")
                break # End the run

        # After loop finishes (max_turns reached or break)
        logger.debug(f"Streaming run completed after {turn} turns. Total history size: {len(history)} messages.")
        # Yield the final aggregated response structure
        yield {"response": Response(messages=history[init_len:], agent=active_agent, context_variables=context_variables)}

    async def run(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        context_variables: dict = {},
        model_override: Optional[str] = None,
        stream: bool = False, # Default to non-streaming
        debug: bool = False,
        max_turns: int = float("inf"), # Allow infinite turns
        execute_tools: bool = True
    ) -> Response:
        """
        Execute the swarm run in streaming or non-streaming mode.

        Args:
            agent: Starting agent.
            messages: Initial conversation history.
            context_variables: Variables to include in the context.
            model_override: Optional model to override default.
            stream: If True, return an async generator; otherwise, return a single Response object.
            debug: If True, log detailed execution information.
            max_turns: Maximum number of agent turns to process.
            execute_tools: If True, execute tool calls requested by the agent.

        Returns:
            Response or AsyncGenerator: Final response object, or an async generator if stream=True.
        """
        if not agent:
            logger.error("Cannot run: Agent is None")
            raise ValueError("Agent is required")

        effective_debug = debug or self.debug
        logger.debug(f"Starting run for agent '{agent.name}' with {len(messages)} messages, stream={stream}")

        # Handle streaming case by returning the generator
        if stream:
            # We return the async generator directly when stream=True
            return self.run_and_stream(
                agent=agent, messages=messages, context_variables=context_variables,
                model_override=model_override, debug=effective_debug, max_turns=max_turns, execute_tools=execute_tools
            )

        # --- Non-Streaming Execution ---
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        if not isinstance(context_variables, dict):
            logger.warning(f"Invalid context_variables type: {type(context_variables)}. Using empty dict.")
            context_variables = {}
        context_variables["active_agent_name"] = active_agent.name

        # Discover tools and resources for initial agent if not done
        if not hasattr(active_agent, '_tools_discovered'):
             active_agent.functions = await discover_and_merge_agent_tools(active_agent, self.config, effective_debug)
             active_agent._tools_discovered = True
        if not hasattr(active_agent, '_resources_discovered'):
            active_agent.resources = await discover_and_merge_agent_resources(active_agent, self.config, effective_debug)
            active_agent._resources_discovered = True

        turn = 0
        while turn < max_turns:
            turn += 1
            logger.debug(f"Turn {turn} starting with agent '{active_agent.name}'.")
            # Get a single, complete chat completion message
            message = await get_chat_completion_message(
                self.client, active_agent, history, context_variables, self.current_llm_config,
                self.max_context_tokens, self.max_context_messages, model_override, stream=False, debug=effective_debug
            )
            # Ensure message has sender info (might be redundant if get_chat_completion_message does it)
            message.sender = active_agent.name
            # Add the assistant's response to history
            history.append(json.loads(message.model_dump_json()))

            # --- Tool Execution Phase ---
            if message.tool_calls and execute_tools:
                logger.debug(f"Turn {turn}: Agent '{active_agent.name}' requested {len(message.tool_calls)} tool calls.")
                # Execute tools
                partial_response = await handle_tool_calls(message.tool_calls, active_agent.functions, context_variables, effective_debug)
                # Add tool results to history
                history.extend(partial_response.messages)
                # Update context variables
                context_variables.update(partial_response.context_variables)

                # Check for agent handoff
                if partial_response.agent and partial_response.agent != active_agent:
                    active_agent = partial_response.agent
                    context_variables["active_agent_name"] = active_agent.name # Update context
                    logger.debug(f"Turn {turn}: Agent handoff to '{active_agent.name}' detected.")
                    # Discover tools/resources for the new agent if needed
                    if not hasattr(active_agent, '_tools_discovered'):
                        active_agent.functions = await discover_and_merge_agent_tools(active_agent, self.config, effective_debug)
                        active_agent._tools_discovered = True
                    if not hasattr(active_agent, '_resources_discovered'):
                        active_agent.resources = await discover_and_merge_agent_resources(active_agent, self.config, effective_debug)
                        active_agent._resources_discovered = True

                # Continue loop for next turn if tools were called
                logger.debug(f"Turn {turn}: Continuing loop after tool execution.")
                continue

            else: # No tool calls or execution disabled
                 logger.debug(f"Turn {turn}: No tool calls requested or execution disabled. Ending run.")
                 break # End the run

        # After loop finishes
        logger.debug(f"Non-streaming run completed after {turn} turns. Total history size: {len(history)} messages.")
        # Create the final Response object containing only the new messages
        final_response = Response(
            id=f"response-{uuid.uuid4()}", # Generate unique ID
            messages=history[init_len:], # Only messages added during this run
            agent=active_agent, # The agent that produced the last message
            context_variables=context_variables # Final context state
        )
        if effective_debug:
            logger.debug(f"Final Response ID: {final_response.id}, Messages count: {len(final_response.messages)}")
        return final_response
