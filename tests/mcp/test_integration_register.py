import importlib
import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock


def test_register_blueprints_with_mcp(monkeypatch):
    # Fake discovery with one blueprint
    fake_discovered = {
        "suggestion": {
            "metadata": {"name": "Suggestion", "description": "Provide suggestions"},
            "class_type": Mock
        },
    }

    # Stub registry module
    reg_pkg = ModuleType("django_mcp_server")
    reg_mod = ModuleType("django_mcp_server.registry")
    calls = []

    def register_tool(name, parameters, description, handler):  # noqa: D401
        calls.append({"name": name, "parameters": parameters, "description": description, "handler": handler})

    # Add the register_tool function to the module's namespace
    reg_mod.register_tool = register_tool  # type: ignore
    reg_pkg.registry = reg_mod  # type: ignore
    sys.modules["django_mcp_server"] = reg_pkg
    sys.modules["django_mcp_server.registry"] = reg_mod

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    # Create a mock blueprint class for the test
    mock_blueprint_cls = Mock()
    fake_discovered["suggestion"]["class_type"] = mock_blueprint_cls

    # Mock the blueprint instance and its run method
    mock_blueprint_instance = Mock()
    mock_blueprint_cls.return_value = mock_blueprint_instance

    async def mock_run(messages, mcp_servers_override=None):
        return [{"messages": [{"role": "assistant", "content": "Hi there! How can I help with your instruction?"}]}]

    mock_blueprint_instance.run = AsyncMock(side_effect=mock_run)

    from swarm.mcp import integration as integ
    importlib.reload(integ)
    count = integ.register_blueprints_with_mcp()

    assert count == 1
    assert calls and calls[0]["name"] == "suggestion"
    # Call handler to ensure it wires through to provider
    result = calls[0]["handler"]({"instruction": "Hi"})
    assert "instruction" in result["content"].lower()

