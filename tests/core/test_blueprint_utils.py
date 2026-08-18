import pytest

from swarm.core.blueprint_utils import BlueprintFunctionTool, filter_blueprints


def test_filter_blueprints_happy_path():
    """Test filtering with multiple valid keys."""
    blueprints = {"bp1": "data1", "bp2": "data2", "bp3": "data3"}
    allowed = "bp1,bp3"
    result = filter_blueprints(blueprints, allowed)
    assert result == {"bp1": "data1", "bp3": "data3"}


class _FakeBlueprint:
    """Minimal blueprint stand-in for BlueprintFunctionTool."""

    def __init__(self, blueprint_id, config=None, **kwargs):
        self.blueprint_id = blueprint_id

    async def run(self, messages, **kwargs):
        content = messages[-1]["content"] if messages else ""
        yield {"messages": [{"role": "assistant", "content": f"echo:{content}"}]}


def test_blueprint_function_tool_uses_class_type_from_discovery_dict(monkeypatch):
    """discover_blueprints returns DiscoveredBlueprintInfo dicts, not classes."""
    discovered = {
        "demo": {
            "class_type": _FakeBlueprint,
            "metadata": {"name": "demo"},
        }
    }
    monkeypatch.setattr(
        "swarm.core.blueprint_utils.discover_blueprints",
        lambda _dir: discovered,
    )

    tool = BlueprintFunctionTool("demo")
    result = tool("hello")
    assert result == "echo:hello"


def test_blueprint_function_tool_missing_raises(monkeypatch):
    monkeypatch.setattr(
        "swarm.core.blueprint_utils.discover_blueprints",
        lambda _dir: {},
    )
    tool = BlueprintFunctionTool("missing")
    with pytest.raises(ValueError, match="not found"):
        tool("hello")

def test_filter_blueprints_empty_dict():
    """Test filtering an empty dictionary."""
    assert filter_blueprints({}, "bp1") == {}

def test_filter_blueprints_empty_allowed():
    """Test filtering with an empty allowed string."""
    assert filter_blueprints({"bp1": "data1"}, "") == {}

def test_filter_blueprints_whitespace():
    """Test filtering with extra whitespace in the allowed string."""
    blueprints = {"bp1": "data1", "bp2": "data2"}
    # The implementation uses .strip(), so this should work
    assert filter_blueprints(blueprints, " bp1 ,  bp2  ") == blueprints

def test_filter_blueprints_duplicate_keys():
    """Test filtering with duplicate keys in the allowed string."""
    blueprints = {"bp1": "data1", "bp2": "data2"}
    assert filter_blueprints(blueprints, "bp1,bp1,bp2") == blueprints

def test_filter_blueprints_non_existent_keys():
    """Test filtering with keys not present in the dictionary."""
    blueprints = {"bp1": "data1"}
    assert filter_blueprints(blueprints, "bp1,bp2,bp3") == {"bp1": "data1"}

def test_filter_blueprints_case_sensitivity():
    """Test that filtering is case-sensitive."""
    blueprints = {"bp1": "data1", "BP1": "DATA1"}
    assert filter_blueprints(blueprints, "bp1") == {"bp1": "data1"}
    assert filter_blueprints(blueprints, "BP1") == {"BP1": "DATA1"}

def test_filter_blueprints_none_allowed():
    """Test that passing None for allowed_blueprints_str raises AttributeError."""
    with pytest.raises(AttributeError):
        filter_blueprints({"bp1": "data1"}, None)
