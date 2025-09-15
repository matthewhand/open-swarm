import pytest


def test_provider_lists_tools(monkeypatch):
    # Fake discovery result with minimal metadata
    fake_discovered = {
        "suggestion": {"metadata": {"name": "Suggestion", "description": "Provide suggestions"}},
        "codey": {"metadata": {"name": "Codey", "description": "Coding assistant"}},
    }

    from swarm.mcp import provider as prov

    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)
    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")
    tools = p.list_tools()
    names = {t["name"] for t in tools}
    assert {"suggestion", "codey"} == names
    sug = next(t for t in tools if t["name"] == "suggestion")
    assert "instruction" in sug["parameters"]["properties"]


def test_provider_call_tool(monkeypatch):
    fake_discovered = {
        "suggestion": {"metadata": {"name": "Suggestion", "description": "Provide suggestions"}},
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")
    result = p.call_tool("suggestion", {"instruction": "Hello"})
    assert "Suggestion" in p._index["suggestion"]["name"]
    assert "Hello" in result["content"]

    with pytest.raises(ValueError):
        p.call_tool("unknown", {"instruction": "x"})
    with pytest.raises(ValueError):
        p.call_tool("suggestion", {"instruction": ""})

