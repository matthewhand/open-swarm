import importlib
import sys
from types import ModuleType


def test_register_blueprints_with_mcp(monkeypatch):
    # Fake discovery with one blueprint
    fake_discovered = {
        "suggestion": {"metadata": {"name": "Suggestion", "description": "Provide suggestions"}},
    }

    # Stub registry module
    reg_pkg = ModuleType("django_mcp_server")
    reg_mod = ModuleType("django_mcp_server.registry")
    calls = []

    def register_tool(name, parameters, description, handler):  # noqa: D401
        calls.append({"name": name, "parameters": parameters, "description": description, "handler": handler})

    reg_mod.register_tool = register_tool
    sys.modules["django_mcp_server"] = reg_pkg
    sys.modules["django_mcp_server.registry"] = reg_mod

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    from swarm.mcp import integration as integ
    importlib.reload(integ)
    count = integ.register_blueprints_with_mcp()

    assert count == 1
    assert calls and calls[0]["name"] == "suggestion"
    # Call handler to ensure it wires through to provider
    result = calls[0]["handler"]({"instruction": "Hi"})
    assert "instruction" in result["content"].lower()

