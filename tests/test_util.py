from swarm.util import function_to_json

def test_function_to_json_callable():
    def example_function(a: int, b: str) -> None:
        pass
    result = function_to_json(example_function)
    assert result["type"] == "function"
    assert result["function"]["name"] == "example_function"
    assert result["function"]["description"] == "Calls example_function"

def test_merge_chunk():
    final_response = {"content": "", "tool_calls": {}}
    delta = {"content": "Hello"}
    from swarm.util import merge_chunk
    merge_chunk(final_response, delta)
    assert final_response["content"] == "Hello"
