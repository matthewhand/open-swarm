from unittest.mock import AsyncMock, Mock, patch

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
        "suggestion": {
            "metadata": {"name": "Suggestion", "description": "Provide suggestions"},
            "class_type": Mock
        },
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    # Create provider instance
    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")

    # Mock the blueprint class and instance
    mock_blueprint_cls = Mock()
    p._index["suggestion"]["class_type"] = mock_blueprint_cls

    mock_blueprint_instance = Mock()
    mock_blueprint_cls.return_value = mock_blueprint_instance

    # Mock the async run method to return test data
    async def mock_run(messages, mcp_servers_override=None):
        return [{"messages": [{"role": "assistant", "content": "Hello"}]}]

    mock_blueprint_instance.run = AsyncMock(side_effect=mock_run)

    result = p.call_tool("suggestion", {"instruction": "Hello"})
    assert "Suggestion" in p._index["suggestion"]["name"]
    assert "Hello" in result["content"]

    with pytest.raises(ValueError):
        p.call_tool("unknown", {"instruction": "x"})
    with pytest.raises(ValueError):
        p.call_tool("suggestion", {"instruction": ""})


def test_provider_call_tool_nebula_shellz_integration(monkeypatch):
    """Integration test for BlueprintMCPProvider.call_tool() with nebula_shellz blueprint."""
    # Mock the nebula_shellz blueprint discovery
    fake_discovered = {
        "nebula_shellz": {
            "metadata": {
                "name": "NebulaShellzzarBlueprint",
                "description": "A multi-agent blueprint inspired by The Matrix for system administration and coding tasks.",
                "required_mcp_servers": ["memory"]
            },
            "class_type": Mock
        }
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    # Create provider instance
    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")

    # Mock the blueprint class and its metadata
    mock_blueprint_cls = Mock()
    mock_blueprint_cls.metadata = {"required_mcp_servers": ["memory"]}
    p._index["nebula_shellz"]["class_type"] = mock_blueprint_cls

    # Mock blueprint instance
    mock_blueprint_instance = Mock()
    mock_blueprint_cls.return_value = mock_blueprint_instance

    # Mock the async run method to return test data
    async def mock_run(messages, mcp_servers_override=None):
        return [{"messages": [{"role": "assistant", "content": "Matrix operation completed"}]}]

    mock_blueprint_instance.run = AsyncMock(side_effect=mock_run)

    # Mock MCP server management methods
    with patch.object(p, '_start_required_mcp_servers', return_value=["mock_memory_server"]) as mock_start, \
         patch.object(p, '_stop_started_servers') as mock_stop:

        # Call the tool
        result = p.call_tool("nebula_shellz", {"instruction": "Execute matrix command"})

        # Verify MCP servers were started and stopped
        mock_start.assert_called_once_with(["memory"])
        mock_stop.assert_called_once_with(["mock_memory_server"])

        # Verify blueprint was instantiated and run
        mock_blueprint_cls.assert_called_once()
        assert result["content"] == "Matrix operation completed"


def test_provider_call_tool_nebula_shellz_execution_flow(monkeypatch):
    """Test the complete execution flow for nebula_shellz blueprint with MCP server lifecycle."""
    # Mock the nebula_shellz blueprint discovery
    fake_discovered = {
        "nebula_shellz": {
            "metadata": {
                "name": "NebulaShellzzarBlueprint",
                "description": "A multi-agent blueprint inspired by The Matrix for system administration and coding tasks.",
                "required_mcp_servers": ["memory", "filesystem"]
            },
            "class_type": Mock
        }
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    # Create provider instance
    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")

    # Mock the blueprint class and its metadata
    mock_blueprint_cls = Mock()
    mock_blueprint_cls.metadata = {"required_mcp_servers": ["memory", "filesystem"]}
    p._index["nebula_shellz"]["class_type"] = mock_blueprint_cls

    # Mock blueprint instance with multiple async chunks
    mock_blueprint_instance = Mock()
    mock_blueprint_cls.return_value = mock_blueprint_instance

    async def mock_run(messages, mcp_servers_override=None):
        return [
            {"messages": [{"role": "assistant", "content": "Initializing Matrix agents..."}]},
            {"messages": [{"role": "assistant", "content": "Neo: Code review complete"}]},
            {"messages": [{"role": "assistant", "content": "Trinity: Shell command executed"}]}
        ]

    mock_blueprint_instance.run = AsyncMock(side_effect=mock_run)

    # Mock MCP server management
    with patch.object(p, '_start_required_mcp_servers', return_value=["mock_memory_server", "mock_filesystem_server"]) as mock_start, \
         patch.object(p, '_stop_started_servers') as mock_stop:

        # Call the tool
        result = p.call_tool("nebula_shellz", {"instruction": "Run comprehensive system analysis"})

        # Verify MCP servers were managed correctly
        mock_start.assert_called_once_with(["memory", "filesystem"])
        mock_stop.assert_called_once_with(["mock_memory_server", "mock_filesystem_server"])

        # Verify the result combines all async chunks
        expected_content = "Initializing Matrix agents...\nNeo: Code review complete\nTrinity: Shell command executed"
        assert result["content"] == expected_content


def test_provider_call_tool_nebula_shellz_error_handling(monkeypatch):
    """Test error handling in nebula_shellz blueprint execution."""
    # Mock the nebula_shellz blueprint discovery
    fake_discovered = {
        "nebula_shellz": {
            "metadata": {
                "name": "NebulaShellzzarBlueprint",
                "description": "A multi-agent blueprint inspired by The Matrix for system administration and coding tasks.",
                "required_mcp_servers": ["memory"]
            },
            "class_type": Mock
        }
    }

    from swarm.mcp import provider as prov
    monkeypatch.setattr(prov, "discover_blueprints", lambda _: fake_discovered)

    # Create provider instance
    p = prov.BlueprintMCPProvider(blueprint_dir="ignored")

    # Mock the blueprint class
    mock_blueprint_cls = Mock()
    mock_blueprint_cls.metadata = {"required_mcp_servers": ["memory"]}
    p._index["nebula_shellz"]["class_type"] = mock_blueprint_cls

    # Mock blueprint instance that raises an exception
    mock_blueprint_instance = Mock()
    mock_blueprint_cls.return_value = mock_blueprint_instance

    async def mock_run(messages, mcp_servers_override=None):
        # Simulate an error by raising an exception
        raise RuntimeError("Matrix glitch detected")

    mock_blueprint_instance.run = AsyncMock(side_effect=mock_run)

    # Mock MCP server management
    with patch.object(p, '_start_required_mcp_servers', return_value=["mock_memory_server"]) as mock_start, \
         patch.object(p, '_stop_started_servers') as mock_stop:

        # Call the tool - should handle the exception gracefully
        result = p.call_tool("nebula_shellz", {"instruction": "Execute failing command"})

        # Verify MCP servers were still managed (cleanup should happen even on error)
        mock_start.assert_called_once_with(["memory"])
        mock_stop.assert_called_once_with(["mock_memory_server"])

        # Verify error is handled and returned in result
        assert "[Blueprint:nebula_shellz] Execution error:" in result["content"]
        assert "Matrix glitch detected" in result["content"]

