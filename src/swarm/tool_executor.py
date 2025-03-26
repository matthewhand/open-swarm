"""
Tool execution utilities for the Swarm framework.
Handles invoking agent functions/tools based on LLM requests.
"""

import json
import logging
import inspect # To check for awaitables
from typing import List, Dict, Any, Optional, Union

# Import necessary types from the Swarm framework
from .types import (
    ChatCompletionMessageToolCall,
    Agent,
    AgentFunction, # Type hint for functions/tools
    Response, # Structure for returning results of multiple tool calls
    Result # Structure for returning result of a single tool call
)
# Utility to convert function signatures to JSON schema (if needed, though less common now with direct calls)
# from .util import function_to_json # Commented out if not used directly here

# Configure module-level logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG) # Uncomment for verbose logging
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Standard name used for injecting context variables into tool calls
__CTX_VARS_NAME__ = "context_variables"


def handle_function_result(result: Any, debug: bool) -> Result:
    """
    Process the raw result returned by an agent function/tool into a standardized Result object.
    Handles agent handoffs if the result is an Agent instance.

    Args:
        result: The raw return value from the executed function/tool.
        debug: If True, log detailed information about the result processing.

    Returns:
        Result: A standardized Result object containing the processed value,
                potential agent handoff, and context variable updates.

    Raises:
        TypeError: If the raw result cannot be cast to a string for the Result value.
    """
    if debug:
        # Log raw result type and a preview (truncated for brevity)
        try:
            result_preview = str(result)[:100] + ('...' if len(str(result)) > 100 else '')
        except Exception:
            result_preview = "[Could not convert result to string for preview]"
        logger.debug(f"Processing function result. Type: {type(result)}, Preview: {result_preview}")

    # Check if the result is already a Result object
    if isinstance(result, Result):
        if debug: logger.debug("Result is already a Result object. Returning as is.")
        return result
    # Check if the result indicates an agent handoff
    elif isinstance(result, Agent):
        agent_name = getattr(result, 'name', 'UnnamedAgent')
        if debug: logger.debug(f"Result is an Agent handoff to: '{agent_name}'")
        # Create a Result object indicating the handoff
        # The 'value' might represent the confirmation or status of the handoff itself
        return Result(value=json.dumps({"status": f"Handoff to agent {agent_name} initiated."}), agent=result)
    # Handle other types (attempt to serialize to string)
    else:
        try:
            # Convert the result to a JSON string if possible, otherwise just stringify
            # JSON is generally preferred for structured tool responses
            if isinstance(result, (dict, list, tuple)):
                 result_str = json.dumps(result)
            else:
                 result_str = str(result)

            if debug: logger.debug(f"Converted result to string/JSON: {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
            # Return a Result object with the stringified value
            return Result(value=result_str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize or cast function result to string/JSON: {e}", exc_info=debug)
            # Raise a TypeError if conversion fails, indicating an issue with the tool's return type
            raise TypeError(f"Tool function returned a result of type {type(result)} that could not be serialized to string/JSON: {result}") from e


async def handle_tool_calls(
    tool_calls: List[ChatCompletionMessageToolCall], # Expect list of Pydantic models
    functions: List[AgentFunction], # Available functions/tools for the agent
    context_variables: dict, # Current context
    debug: bool # Debug logging flag
) -> Response:
    """
    Execute a list of tool calls requested by the LLM and aggregate their results.

    Args:
        tool_calls: A list of ChatCompletionMessageToolCall objects requested by the LLM.
        functions: A list of available functions/tools (callables or dicts) for the current agent.
        context_variables: A dictionary containing the current context variables.
        debug: If True, enable detailed debugging logs.

    Returns:
        Response: An object containing a list of messages (tool results) to be added
                  to the conversation history, the potentially changed agent (due to handoff),
                  and any updates to context variables from the tool calls.
    """
    # Basic validation of input
    if not tool_calls or not isinstance(tool_calls, list):
        logger.debug("No valid tool calls provided to handle_tool_calls.")
        # Return an empty Response if there's nothing to process
        return Response(messages=[], agent=None, context_variables={})

    logger.debug(f"Handling {len(tool_calls)} tool calls.")

    # Create a mapping from function/tool name to the actual callable object
    function_map: Dict[str, AgentFunction] = {}
    for func in functions:
         # Get name robustly (prefer 'name' attribute, fallback to __name__)
         func_name = getattr(func, 'name', getattr(func, '__name__', None))
         if func_name:
             if func_name in function_map:
                  logger.warning(f"Duplicate function/tool name '{func_name}' detected. Overwriting previous entry.")
             function_map[func_name] = func
         else:
              logger.warning(f"Available function/tool object {func} is missing a valid name. Skipping.")

    # Initialize Response object to aggregate results
    aggregated_response = Response(messages=[], agent=None, context_variables={})

    # Process each requested tool call
    for tool_call in tool_calls:
        # Ensure it's the expected Pydantic model type
        if not isinstance(tool_call, ChatCompletionMessageToolCall):
            logger.warning(f"Skipping invalid item in tool_calls list: Expected ChatCompletionMessageToolCall, got {type(tool_call)}.")
            continue

        # Extract necessary info from the tool call object
        tool_name = getattr(tool_call.function, 'name', None)
        tool_call_id = getattr(tool_call, 'id', None)
        raw_arguments = getattr(tool_call.function, 'arguments', '{}') # Default to empty JSON object string

        # Validate essential components
        if not tool_name or not tool_call_id:
            logger.error(f"Invalid tool call data: Missing name ('{tool_name}') or id ('{tool_call_id}'). Skipping.")
            # Optionally add an error message to the response
            aggregated_response.messages.append({
                "role": "tool", "tool_call_id": tool_call_id or "missing_id", "name": tool_name or "missing_name",
                "content": json.dumps({"error": "Invalid tool call data received from LLM."})
            })
            continue

        # Find the corresponding function/tool in the map
        func_to_call = function_map.get(tool_name)
        if not func_to_call:
            logger.error(f"Tool '{tool_name}' requested by LLM (ID: '{tool_call_id}') not found in agent's available functions.")
            # Add error message to history
            aggregated_response.messages.append({
                "role": "tool", "tool_call_id": tool_call_id, "name": tool_name,
                "content": json.dumps({"error": f"Tool '{tool_name}' is not available."}) # Use JSON for content
            })
            continue

        # Parse arguments string into a dictionary
        try:
            args: Dict[str, Any] = json.loads(raw_arguments)
            if not isinstance(args, dict):
                logger.warning(f"Parsed arguments for tool '{tool_name}' is not a dictionary ({type(args)}). Using empty dict.")
                args = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON arguments for tool '{tool_name}' (ID: '{tool_call_id}'): {e}. Raw args: '{raw_arguments}'. Using empty dict.")
            args = {}

        # Inject context variables if the function expects them
        try:
             sig = inspect.signature(func_to_call)
             if __CTX_VARS_NAME__ in sig.parameters:
                 args[__CTX_VARS_NAME__] = context_variables
                 if debug: logger.debug(f"Injecting context variables into tool '{tool_name}'.")
        except (ValueError, TypeError) as e:
             # Handle cases where signature cannot be inspected (e.g., built-ins)
             logger.warning(f"Could not inspect signature for tool '{tool_name}': {e}. Cannot inject context automatically.")


        # --- Execute the function/tool ---
        try:
            logger.info(f"Executing tool '{tool_name}' (ID: '{tool_call_id}') with args: {redact_sensitive_data(args)}")
            # Execute the function with parsed arguments
            raw_result = func_to_call(**args)

            # Handle asynchronous functions/tools if necessary
            if inspect.isawaitable(raw_result):
                if debug: logger.debug(f"Awaiting async result for tool '{tool_name}' (ID: '{tool_call_id}')")
                raw_result = await raw_result
            # else: (sync function executed directly)

            # Process the raw result (handles handoffs, serialization)
            processed_result: Result = handle_function_result(raw_result, debug)

            # Add the processed result message to the response
            # Ensure content is a JSON string as expected by OpenAI 'tool' role message
            result_content_json = processed_result.value if isinstance(processed_result.value, str) else json.dumps(processed_result.value)
            aggregated_response.messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": result_content_json
            })

            # Update context variables from the result
            if processed_result.context_variables:
                 aggregated_response.context_variables.update(processed_result.context_variables)
                 if debug: logger.debug(f"Updated context variables from tool '{tool_name}': {processed_result.context_variables.keys()}")

            # Handle potential agent handoff indicated by the result
            if processed_result.agent:
                 # If multiple tool calls try to handoff, the last one 'wins' here
                 if aggregated_response.agent and aggregated_response.agent != processed_result.agent:
                      logger.warning(f"Multiple agent handoffs detected in one turn. Last handoff to '{getattr(processed_result.agent, 'name', 'UnnamedAgent')}' takes precedence.")
                 aggregated_response.agent = processed_result.agent
                 # Update context immediately for subsequent steps within this turn if needed
                 context_variables["active_agent_name"] = getattr(processed_result.agent, 'name', None)
                 logger.debug(f"Agent handoff triggered by tool '{tool_name}' to agent '{context_variables['active_agent_name']}'.")

        except Exception as e:
            # Catch errors during function execution
            logger.error(f"Error executing tool '{tool_name}' (ID: '{tool_call_id}'): {e}", exc_info=debug)
            # Add error message to the response history
            aggregated_response.messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": json.dumps({"error": f"Execution failed: {str(e)}"}) # Provide error in JSON content
            })

    # Return the aggregated response containing all tool result messages and potential updates
    logger.debug(f"Finished handling tool calls. {len(aggregated_response.messages)} result messages generated.")
    return aggregated_response
