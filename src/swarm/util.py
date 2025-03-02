"""
Utility functions for the Swarm framework.

This module provides helper functions for serializing functions/tools to JSON and merging streaming response chunks,
ensuring compatibility with OpenAI API requirements and robust handling of agent interactions.
"""

import inspect
import json
from datetime import datetime
from .types import Tool  # Adjust import as needed if 'Tool' is in a different location


def merge_fields(target: dict, source: dict) -> None:
    """
    Recursively merge fields from source into target, appending strings and updating nested dictionaries.

    Args:
        target (dict): The dictionary to update.
        source (dict): The dictionary with new values to merge.
    """
    for key, value in source.items():
        if isinstance(value, str):
            target[key] = target.get(key, "") + value
        elif value is not None and isinstance(value, dict):
            if key not in target:
                target[key] = {}
            merge_fields(target[key], value)


def merge_chunk(final_response: dict, delta: dict) -> None:
    """
    Merge a delta update into a response dictionary, handling tool calls and content incrementally.

    Args:
        final_response (dict): The cumulative response being built.
        delta (dict): The delta update from a streaming response.
    """
    delta.pop("role", None)
    merge_fields(final_response, delta)

    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index", 0)
        if "tool_calls" not in final_response:
            final_response["tool_calls"] = {}
        if index not in final_response["tool_calls"]:
            final_response["tool_calls"][index] = {"function": {"arguments": "", "name": ""}, "id": "", "type": ""}
        merge_fields(final_response["tool_calls"][index], tool_calls[0])


def function_to_json(func, truncate_desc: bool = False) -> dict:
    """
    Convert a Python callable or Tool instance to a JSON-serializable dictionary for OpenAI API.

    Supports both reflection-based serialization for raw functions and schema-based serialization for Tool objects.
    Optionally truncates descriptions to 1024 characters to meet API limits.

    Args:
        func: The function or Tool object to serialize.
        truncate_desc (bool): If True, truncate the description to 1024 characters.

    Returns:
        dict: A dictionary with 'type', 'function', 'name', 'description', and 'parameters'.

    Raises:
        ValueError: If function signature cannot be inspected (for raw functions).
    """
    # Handle Tool instances from MCP servers
    if isinstance(func, Tool):
        name = func.name
        description = func.description or ""
        tool_schema = func.input_schema or {}
        final_type = tool_schema.get("type", "object")
        final_properties = tool_schema.get("properties", {})
        final_required = tool_schema.get("required", [])
    # Handle raw Python callables via reflection
    else:
        try:
            signature = inspect.signature(func)
        except ValueError as e:
            raise ValueError(f"Failed to get signature for function {func.__name__}: {str(e)}")
        
        name = getattr(func, "__name__", "unnamed_function")
        description = (func.__doc__ or "").strip() or f"Calls {name}"
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }
        parameters = {}
        required = []
        for param in signature.parameters.values():
            ann = param.annotation if param.annotation != inspect.Parameter.empty else str
            param_type = type_map.get(ann, "string")
            parameters[param.name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(param.name)
        
        final_type = "object"
        final_properties = parameters
        final_required = required

    # Truncate description if requested
    if truncate_desc and len(description) > 1024:
        description = description[:1024]
        # logger.debug(f"Truncated description for '{name}': {len(description)} -> 1024 characters")

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": final_type,
                "properties": final_properties,
                "required": final_required,
            },
        },
    }
