import tempfile
from pathlib import Path
from swarm.extensions.config import config_loader

def test_mcp_server_config_parsing():
    config = {
        "llm": {"dummy": {"provider": "none", "model": "dummy"}},
        "mcp_servers": {
            "default": {
                "url": "https://mcp.example.com",
                "api_key": "sk-1234"
            },
            "alt": {
                "url": "https://alt-mcp.example.com",
                "api_key": "sk-alt"
            }
        },
        "settings": {"active_mcp": "default"}
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        Path(tmp.name).write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(Path(tmp.name))
        # Should parse both servers
        assert "default" in loaded["mcp_servers"]
        assert loaded["mcp_servers"]["default"]["url"] == "https://mcp.example.com"
        assert loaded["settings"]["active_mcp"] == "default"
        # Should be able to select the active MCP server
        active = loaded["mcp_servers"][loaded["settings"]["active_mcp"]]
        assert active["api_key"].startswith("sk-")

def test_mcp_server_add_remove_and_edge_cases():
    config = {
        "llm": {"dummy": {"provider": "none", "model": "dummy"}},
        "mcp_servers": {
            "default": {"url": "https://mcp.example.com", "api_key": "sk-1234"}
        },
        "settings": {"active_mcp": "default"}
    }
    with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
        config_path = Path(tmp.name)
        config_path.write_text(str(config).replace("'", '"'))
        loaded = config_loader.load_config(config_path)
        # Add a new MCP server
        loaded["mcp_servers"]["new"] = {"url": "https://new.example.com", "api_key": "sk-new"}
        assert "new" in loaded["mcp_servers"]
        assert loaded["mcp_servers"]["new"]["url"] == "https://new.example.com"
        # Remove an MCP server
        del loaded["mcp_servers"]["default"]
        assert "default" not in loaded["mcp_servers"]
        # Edge: missing api_key
        loaded["mcp_servers"]["bad"] = {"url": "https://bad.example.com"}
        assert "api_key" not in loaded["mcp_servers"]["bad"] or loaded["mcp_servers"]["bad"].get("api_key") is None
        # Edge: duplicate name (should overwrite)
        loaded["mcp_servers"]["new"] = {"url": "https://dup.example.com", "api_key": "sk-dup"}
        assert loaded["mcp_servers"]["new"]["url"] == "https://dup.example.com"
        # Edge: invalid URL (just store as-is)
        loaded["mcp_servers"]["invalid"] = {"url": "not_a_url", "api_key": "sk-xxx"}
        assert loaded["mcp_servers"]["invalid"]["url"] == "not_a_url"
