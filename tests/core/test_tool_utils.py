import pytest
import inspect
from typing import List, Dict, Optional, Any, Union
from unittest.mock import patch
from swarm.core.tool_utils import get_function_schema, tool

def test_get_function_schema_basic():
    def basic_func(a: str, b: int):
        """
        A basic function.
        """
        return a * b

    schema = get_function_schema(basic_func)
    assert schema["name"] == "basic_func"
    assert schema["description"] == "A basic function."
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"]["a"]["type"] == "string"
    assert schema["parameters"]["properties"]["b"]["type"] == "integer"
    assert "a" in schema["parameters"]["required"]
    assert "b" in schema["parameters"]["required"]

def test_get_function_schema_types():
    def types_func(
        s: str,
        i: int,
        f: float,
        b: bool,
        l: list,
        d: dict,
        li: List[int],
        ls: List[str],
        la: List[Any],
        lo: List[float]
    ):
        pass

    schema = get_function_schema(types_func)
    props = schema["parameters"]["properties"]
    assert props["s"]["type"] == "string"
    assert props["i"]["type"] == "integer"
    assert props["f"]["type"] == "number"
    assert props["b"]["type"] == "boolean"
    assert props["l"]["type"] == "array"
    assert props["d"]["type"] == "object"
    assert props["li"]["type"] == "array"
    assert props["li"]["items"]["type"] == "integer"
    assert props["ls"]["type"] == "array"
    assert props["ls"]["items"]["type"] == "string"
    assert props["la"]["type"] == "array"
    assert props["la"]["items"]["type"] == "string"
    assert props["lo"]["type"] == "array"
    assert props["lo"]["items"]["type"] == "number"

def test_get_function_schema_defaults():
    def default_func(a: str, b: int = 10, c: Optional[str] = None):
        pass

    schema = get_function_schema(default_func)
    assert "a" in schema["parameters"]["required"]
    assert "b" not in schema["parameters"]["required"]
    assert "c" not in schema["parameters"]["required"]

def test_get_function_schema_methods():
    class TestClass:
        def method(self, a: str):
            pass

        @classmethod
        def class_method(cls, b: int):
            pass

    schema_method = get_function_schema(TestClass().method)
    assert "self" not in schema_method["parameters"]["properties"]
    assert "a" in schema_method["parameters"]["properties"]

    schema_class_method = get_function_schema(TestClass.class_method)
    assert "cls" not in schema_class_method["parameters"]["properties"]
    assert "b" in schema_class_method["parameters"]["properties"]

def test_get_function_schema_docstring_parsing():
    def doc_func(a: int):
        """
        This is the first line.

        This is the second line.
        """
        pass

    schema = get_function_schema(doc_func)
    assert schema["description"] == "This is the first line."

def test_get_function_schema_optional_handling():
    def opt_func(a: Optional[int] = None):
        pass

    schema = get_function_schema(opt_func)
    # Based on implementation, Union types are skipped and fall back to "string"
    assert schema["parameters"]["properties"]["a"]["type"] == "string"

def test_tool_decorator_basic():
    @tool()
    def my_tool(x: int):
        """My tool description."""
        return x + 1

    assert my_tool._is_tool is True
    assert my_tool._tool_name == "my_tool"
    assert my_tool._tool_schema["name"] == "my_tool"
    assert my_tool._tool_schema["description"] == "My tool description."
    assert my_tool._tool_schema["parameters"]["properties"]["x"]["type"] == "integer"

def test_tool_decorator_custom_name_desc():
    @tool(name="custom_name", description="custom description")
    def another_tool(y: str):
        return y.upper()

    assert another_tool._tool_name == "custom_name"
    assert another_tool._tool_schema["name"] == "custom_name"
    assert another_tool._tool_schema["description"] == "custom description"

@pytest.mark.asyncio
async def test_tool_execution_sync():
    @tool()
    def sync_tool(x: int):
        return x * 2

    result = await sync_tool(5)
    assert result == 10

@pytest.mark.asyncio
async def test_tool_execution_async():
    @tool()
    async def async_tool(x: int):
        return x * 3

    result = await async_tool(5)
    assert result == 15

def test_tool_schema_fallback():
    with patch("swarm.core.tool_utils.get_function_schema", side_effect=Exception("Test error")):
        @tool()
        def fallback_tool(x: int):
            return x

        assert fallback_tool._tool_name == "fallback_tool"
        assert "fallback_tool" in fallback_tool._tool_schema["name"]
        assert "Parameters schema could not be auto-generated" in fallback_tool._tool_schema["description"]
        assert fallback_tool._tool_schema["parameters"] == {"type": "object", "properties": {}}

def test_tool_decorator_wraps_correctly():
    @tool()
    def wrapped_func(a: int):
        """Docstring"""
        return a

    assert wrapped_func.__name__ == "wrapped_func"
    assert wrapped_func.__doc__ == "Docstring"
    assert wrapped_func._is_tool is True
