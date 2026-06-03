import pytest
import asyncio
from typing import Optional, Union, List, Dict
from swarm.core.tool_utils import get_function_schema, tool

def test_get_function_schema_basic_types():
    def basic_func(a: str, b: int, c: float, d: bool):
        """Docstring."""
        pass

    schema = get_function_schema(basic_func)
    assert schema["name"] == "basic_func"
    assert schema["description"] == "Docstring."

    props = schema["parameters"]["properties"]
    assert props["a"]["type"] == "string"
    assert props["b"]["type"] == "integer"
    assert props["c"]["type"] == "number"
    assert props["d"]["type"] == "boolean"

    assert set(schema["parameters"]["required"]) == {"a", "b", "c", "d"}

def test_get_function_schema_collections():
    def coll_func(a: list, b: List[int], c: List[str], d: List[bool], e: List[float], f: dict, g: Dict[str, int]):
        pass

    schema = get_function_schema(coll_func)
    props = schema["parameters"]["properties"]

    assert props["a"]["type"] == "array"
    assert props["a"]["items"] == {"type": "string"} # Default

    assert props["b"]["type"] == "array"
    assert props["b"]["items"] == {"type": "integer"}

    assert props["c"]["type"] == "array"
    assert props["c"]["items"] == {"type": "string"}

    assert props["d"]["type"] == "array"
    assert props["d"]["items"] == {"type": "boolean"}

    assert props["e"]["type"] == "array"
    assert props["e"]["items"] == {"type": "number"}

    assert props["f"]["type"] == "object"
    assert props["f"]["additionalProperties"] is True

    assert props["g"]["type"] == "object"
    assert props["g"]["additionalProperties"] is True

def test_get_function_schema_defaults_and_required():
    def default_func(a: str, b: int = 10, c: str = "hello"):
        pass

    schema = get_function_schema(default_func)
    assert schema["parameters"]["required"] == ["a"]
    assert "b" in schema["parameters"]["properties"]
    assert "c" in schema["parameters"]["properties"]

def test_get_function_schema_skips_self_cls():
    class MyClass:
        def method(self, a: int):
            pass

        @classmethod
        def class_method(cls, b: str):
            pass

    schema_method = get_function_schema(MyClass().method)
    assert "self" not in schema_method["parameters"]["properties"]
    assert "a" in schema_method["parameters"]["properties"]

    schema_class_method = get_function_schema(MyClass.class_method)
    assert "cls" not in schema_class_method["parameters"]["properties"]
    assert "b" in schema_class_method["parameters"]["properties"]

def test_get_function_schema_docstring_parsing():
    def doc_func():
        """
        First paragraph.

        Second paragraph that should be ignored.
        """
        pass

    schema = get_function_schema(doc_func)
    assert schema["description"] == "First paragraph."

def test_get_function_schema_unannotated():
    def unannotated_func(a, b: int):
        pass

    schema = get_function_schema(unannotated_func)
    # Based on code:
    # param_type_annotation = type_hints.get(name) -> returns None for 'a'
    # elif param_type_annotation is None or param_type_annotation == type(None):
    #   schema_type = "null"
    assert schema["parameters"]["properties"]["a"]["type"] == "null"
    assert schema["parameters"]["properties"]["b"]["type"] == "integer"

def test_tool_decorator_basic():
    @tool()
    def my_tool(x: int):
        """This is a tool."""
        return x * 2

    assert hasattr(my_tool, "_tool_schema")
    assert my_tool._is_tool is True
    assert my_tool._tool_name == "my_tool"
    assert my_tool._tool_schema["name"] == "my_tool"
    assert my_tool._tool_schema["description"] == "This is a tool."
    assert "x" in my_tool._tool_schema["parameters"]["properties"]

def test_tool_decorator_overrides():
    @tool(name="custom_name", description="custom description")
    def overridden_tool(x: int):
        pass

    assert overridden_tool._tool_name == "custom_name"
    assert overridden_tool._tool_schema["name"] == "custom_name"
    assert overridden_tool._tool_schema["description"] == "custom description"

@pytest.mark.asyncio
async def test_tool_decorator_execution():
    @tool()
    def sync_tool(x: int):
        return x + 1

    @tool()
    async def async_tool(y: int):
        await asyncio.sleep(0.01)
        return y + 2

    assert await sync_tool(10) == 11
    assert await async_tool(20) == 22

def test_tool_decorator_wraps():
    @tool()
    def wrapped_func(a: int):
        """Docstring."""
        return a

    assert wrapped_func.__name__ == "wrapped_func"
    assert wrapped_func.__doc__ == "Docstring."
    assert wrapped_func._is_tool is True
