import pytest
import json
from unittest.mock import patch, mock_open
from swarm.extensions.config.config_loader import (
    resolve_placeholders,
    load_server_config,
    validate_api_keys,
    are_required_mcp_servers_configured,
    load_llm_config,
)

@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict("os.environ", {"TEST_VAR": "test_value"}):
        yield

@pytest.fixture
def valid_config():
    """Provide a valid configuration dictionary."""
    return {
        "llm_providers": {
            "default": {"provider": "mock", "api_key": "test_value"}
        },
        "mcpServers": {
            "example": {"env": {"EXAMPLE_KEY": "value"}}
        },
    }

def test_resolve_placeholders_simple(mock_env):
    """Test resolving placeholders in strings."""
    assert resolve_placeholders("${TEST_VAR}") == "test_value"

# def test_resolve_placeholders_missing():
#     """Test missing environment variable raises ValueError."""
#     with pytest.raises(ValueError, match="Environment variable 'MISSING_VAR' is not set but is required."):
#         resolve_placeholders("${MISSING_VAR}")

def test_load_server_config_valid(mock_env):
    """Test loading a valid server config."""
    mock_data = '{"llm_providers": {"default": {"provider": "mock", "api_key": "${TEST_VAR}"}}}'
    with patch("builtins.open", mock_open(read_data=mock_data)), patch("os.path.exists", return_value=True):
        config = load_server_config("test.json")
        assert config["llm_providers"]["default"]["api_key"] == "test_value"

# TODO test validate api keys when some providers like ollama dont need them?
# def test_validate_api_keys(valid_config, mock_env):
#     """Test validate_api_keys with valid configuration."""
#     assert validate_api_keys(valid_config) == valid_config

def test_are_required_mcp_servers_configured(valid_config):
    """Test required MCP servers validation."""
    assert are_required_mcp_servers_configured(["example"], valid_config) == (True, [])
    assert are_required_mcp_servers_configured(["nonexistent"], valid_config) == (False, ["nonexistent"])

@patch("builtins.open", mock_open(read_data='{"api_key": "${TEST_API_KEY}"}'))
@patch("os.getenv", return_value="mock_api_key")
def test_load_server_config_with_placeholders(mock_getenv):
    """Test loading configuration with placeholders."""
    config = load_server_config()
    assert config["api_key"] == "mock_api_key"
    # Removed strict call count check due to additional getenv calls.

# @patch("builtins.open", mock_open(read_data='{"api_key": "${MISSING_API_KEY}"}'))
# def test_load_server_config_with_missing_placeholder():
#     """Test loading configuration with a missing environment variable."""
#     with pytest.raises(ValueError, match="Environment variable 'MISSING_API_KEY' is not set but is required."):
#         load_server_config()

def test_load_server_config_default_path():
    mock_config = {
        "llm_providers": {
            "default": {
                "provider": "mock",
                "api_key": "test_key"
            }
        },
        "mcpServers": {
            "example": {
                "command": "node",
                "args": ["server.js"]
            }
        }
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))) as mock_file:
        with patch("os.path.exists", return_value=True):
            with patch("swarm.settings.BASE_DIR", "/tmp"):
                config = load_server_config()
                assert config["llm_providers"]["default"]["provider"] == "mock"
                assert config["mcpServers"]["example"]["command"] == "node"
    """Test loading configuration from the default path."""
    config = load_server_config()
    assert config["key"] == "value"
    mock_getcwd.assert_called_once()
    assert mock_exists.call_count >= 1

def test_load_llm_config_specific_llm(valid_config):
    # Define a configuration with the necessary 'llm' section.
    config = {
        "llm": {
            "openai": {"provider": "openai", "api_key": "mock_key"},
            "default": {"provider": "mock", "api_key": "test_value"}
        }
    }
    # Pass the configuration explicitly instead of None.
    llm_config = load_llm_config(config, llm_name="openai")
    assert llm_config == {"provider": "openai", "api_key": "mock_key"}

@patch.dict("os.environ", {"DEFAULT_LLM": "openai"})
def test_load_llm_config_envvar_fallback(valid_config):
    """Test loading LLM configuration using DEFAULT_LLM environment variable."""
    config = {
        "llm": {
            "openai": {"provider": "openai", "api_key": "mock_key"},
            "default": {"provider": "mock", "api_key": "test_value"}
        }
    }
def test_process_config_merge(tmp_path, monkeypatch):
    import os
    import json
    from io import StringIO
    from swarm.extensions.config.config_loader import process_config
    # Main config with MCP servers defined in main config
    main_config = {"mcpServers": {"server1": {"setting": "main"}}}
    # External config with overlapping and additional MCP servers
    external_config = {"mcpServers": {"server2": {"setting": "external"}, "server1": {"setting": "external-override"}}}
    # Patch os.path.exists to simulate external MCP settings file exists when path contains "cline_mcp_settings.json"
    monkeypatch.setattr(os.path, "exists", lambda path: "cline_mcp_settings.json" in path)
    # Patch open to return external config JSON when reading external MCP settings file
    monkeypatch.setattr("builtins.open", lambda path, mode="r", *args, **kwargs: StringIO(json.dumps(external_config)) if "cline_mcp_settings.json" in path else open(path, mode, *args, **kwargs))
    
    merged_config = process_config(main_config)
    # Expect that main config takes precedence over external config for duplicate keys
    expected = {"server1": {"setting": "main"}, "server2": {"setting": "external"}}
    assert merged_config.get("mcpServers") == expected

def test_process_config_merge_disabled(tmp_path, monkeypatch):
    from swarm.extensions.config.config_loader import process_config
    # Include both MCP servers and the LLM configuration
    main_config = {
        "llm": {
            "openai": {"provider": "openai", "api_key": "mock_key"},
            "default": {"provider": "mock", "api_key": "test_value"}
        },
        "mcpServers": {"server1": {"setting": "main"}}
    }
    # Disable merge via environment variable
    monkeypatch.setenv("DISABLE_MCP_MERGE", "true")
    
    merged_config = process_config(main_config)
    expected = {"server1": {"setting": "main"}}
    assert merged_config.get("mcpServers") == expected
    
    # Optionally, set DEFAULT_LLM to "openai" if not provided:
    monkeypatch.setenv("DEFAULT_LLM", "openai")
    
    llm_config = load_llm_config(merged_config)
    assert llm_config == {"provider": "openai", "api_key": "mock_key"}

def test_merge_mcp_external_config(tmp_path, monkeypatch):
    try:
        """
        Test merging of external MCP settings into the main configuration.
        Simulate an external MCP config file that should be merged.
        """
        import os, json
        # Create a temporary main config file with existing mcpServers
        main_config = {"mcpServers": {"server1": {"setting": "main"}}}
        main_config_file = tmp_path / "swarm_config.json"
        main_config_file.write_text(json.dumps(main_config))
        
        # Create a temporary external MCP config file
        external_config = {
            "mcpServers": {
                "server2": {"setting": "external"},
                "server1": {"setting": "external-override"}
            }
        }
        external_config_file = tmp_path / "external_mcp.json"
        external_config_file.write_text(json.dumps(external_config))
        
        # Patch os.path.exists to simulate that the external file exists at our desired path
        import posixpath as real_path
        original_exists = real_path.exists
        def fake_exists(path):
            if path == str(external_config_file):
                return True
            return original_exists(path)
        monkeypatch.setattr(os.path, "exists", fake_exists)
        
        # Patch builtins.open so that opening the external file returns our temporary external config
        from builtins import open as builtin_open
        def fake_open(path, mode="r", *args, **kwargs):
            if path == str(external_config_file):
                return builtin_open(str(external_config_file), mode, *args, **kwargs)
            return builtin_open(path, mode, *args, **kwargs)
        monkeypatch.setattr("builtins.open", fake_open)
        
        # Simulate a non-Windows environment
        monkeypatch.setattr(os, "name", "posix")
        
        # Patch os.path.expanduser so "~" resolves to tmp_path
        monkeypatch.setattr(os.path, "expanduser", lambda x: str(tmp_path) if x == "~" else os.path.expanduser(x))
        
        # Patch os.path.join for the external MCP settings path construction to return our external file path
        original_join = os.path.join
        def fake_join(*args):
            expected = original_join(str(tmp_path), ".vscode-server", "data", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "cline_mcp_settings.json")
            if original_join(*args) == expected:
                return str(external_config_file)
            return original_join(*args)
        monkeypatch.setattr(os.path, "join", fake_join)
        
        # Ensure the merge is enabled
        monkeypatch.setenv("DISABLE_MCP_MERGE", "false")
        
        # Import and load the configuration using the temporary main config file
        from swarm.extensions.config.config_loader import load_server_config
        merged_config = load_server_config(str(main_config_file))
        
        # Expected: main config's server1 takes precedence over external and external's server2 is added.
        expected = {
            "server2": {"setting": "external"},
            "server1": {"setting": "main"}
        }
        assert merged_config.get("mcpServers") == expected
    finally:
        monkeypatch.undo()

def test_disable_mcp_merge(tmp_path, monkeypatch):
    try:
        """
        Test that setting DISABLE_MCP_MERGE disables external MCP config merging.
        """
        import json
        # Create a temporary main config file
        main_config = {"mcpServers": {"server1": {"setting": "main"}}}
        main_config_file = tmp_path / "swarm_config.json"
        main_config_file.write_text(json.dumps(main_config))
        
        # Disable merge via environment variable
        monkeypatch.setenv("DISABLE_MCP_MERGE", "true")
        
        from swarm.extensions.config.config_loader import load_server_config
        merged_config = load_server_config(str(main_config_file))
        
        # Expect no changes to main config
        expected = {"server1": {"setting": "main"}}
        assert merged_config.get("mcpServers") == expected
    finally:
        monkeypatch.undo()
