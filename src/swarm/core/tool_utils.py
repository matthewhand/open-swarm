import functools
import inspect
import json
from typing import Callable, Any, Dict, List, Optional, get_type_hints, Union

def get_function_schema(func: Callable) -> Dict[str, Any]:
    """
    Generates a JSON schema for a function's parameters.
    This is a simplified version. A more robust version would handle
    more types, default values, and complex annotations.
    """
    sig = inspect.signature(func)
    # For methods, get_type_hints might need the class context if using forward refs
    # For standalone functions or static/class methods, it should be okay.
    try:
        type_hints = get_type_hints(func)
    except Exception: # Broad except for cases where type hints can't be resolved (e.g. complex forward refs)
        type_hints = {}

    parameters_schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    
    for name, param in sig.parameters.items():
        if name == 'self' or name == 'cls': # Skip self/cls for methods
            continue
            
        param_type_annotation = type_hints.get(name)
        schema_type = "string" # Default type
        description = f"Parameter {name}" # Placeholder for descriptions from docstrings

        # Type mapping (simplified)
        if param_type_annotation == str:
            schema_type = "string"
        elif param_type_annotation == int:
            schema_type = "integer"
        elif param_type_annotation == float:
            schema_type = "number"
        elif param_type_annotation == bool:
            schema_type = "boolean"
        elif getattr(param_type_annotation, '__origin__', None) == list or param_type_annotation == list:
            schema_type = "array"
            items_schema = {"type": "string"} # Default item type
            if hasattr(param_type_annotation, '__args__') and param_type_annotation.__args__:
                item_arg_type = param_type_annotation.__args__[0]
                if item_arg_type == str: items_schema = {"type": "string"}
                elif item_arg_type == int: items_schema = {"type": "integer"}
                elif item_arg_type == bool: items_schema = {"type": "boolean"}
                elif item_arg_type == float: items_schema = {"type": "number"}
            parameters_schema["properties"][name] = {"type": schema_type, "description": description, "items": items_schema}
            continue # Skip default property assignment below for arrays
        elif getattr(param_type_annotation, '__origin__', None) == dict or param_type_annotation == dict:
            schema_type = "object"
            # For dicts, further schema definition might be needed if structure is known
            # For now, just mark as object. Add "additionalProperties": True for flexibility.
            parameters_schema["properties"][name] = {"type": schema_type, "description": description, "additionalProperties": True}
            continue # Skip default property assignment below for dicts
        elif param_type_annotation is None or param_type_annotation == type(None):
             # Handle Optional[T] by checking __args__ if it's a Union
            if hasattr(param_type_annotation, '__origin__') and param_type_annotation.__origin__ is Union:
                # Simplified: assume Optional[T] means T or None, take the first non-None type
                # A more robust check would iterate __args__
                pass # Fall through to default string or handle specific T
            else: # Actual NoneType, likely an error or unannotated
                schema_type = "null" # Or treat as string if that's more useful

        parameters_schema["properties"][name] = {"type": schema_type, "description": description}

        if param.default == inspect.Parameter.empty:
            parameters_schema["required"].append(name)
            
    func_description = inspect.getdoc(func)
    if func_description:
        func_description = func_description.split('\n\n')[0].replace('\n', ' ') # First paragraph

    return {
        "name": func.__name__,
        "description": func_description or f"Tool for {func.__name__}",
        "parameters": parameters_schema,
    }

def tool(name: Optional[str] = None, description: Optional[str] = None) -> Callable:
    """
    Decorator to mark a function as a tool and attach schema information.
    The schema is used by LLMs to understand how to call the function.
    """
    def decorator(func: Callable) -> Callable:
        actual_name = name or func.__name__
        
        try:
            schema = get_function_schema(func)
            if description: 
                schema["description"] = description
            if name: 
                schema["name"] = actual_name # Ensure the name in schema matches actual_name

        except Exception as e:
            print(f"Warning: Could not generate detailed schema for tool {actual_name}: {e}")
            schema = {
                "name": actual_name,
                "description": description or f"Tool for {actual_name}. Parameters schema could not be auto-generated.",
                "parameters": {"type": "object", "properties": {}}, # Minimal fallback
            }

        setattr(func, '_tool_schema', schema)
        setattr(func, '_is_tool', True)
        setattr(func, '_tool_name', actual_name)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # If the decorated function is not async, but tools are expected to be awaitable
                # by the agent framework, this might need adjustment.
                # For now, just call it.
                return func(*args, **kwargs)
        
        setattr(wrapper, '_tool_schema', schema)
        setattr(wrapper, '_is_tool', True)
        setattr(wrapper, '_tool_name', actual_name)

        return wrapper
    return decorator
