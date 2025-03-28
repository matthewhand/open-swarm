import pytest  # type: ignore
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import necessary functions from the config_loader module
from swarm.extensions.config.config_loader import (
    load_server_config,
    resolve_placeholders,
    process_config,
    load_llm_config,
    get_llm_model,
    get_server_params,
    list_mcp_servers
)

# Define a base directory for tests if BASE_DIR isn't properly imported/set
try:
    from swarm.settings import BASE_DIR
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent # Adjust if needed


# --- Mocks and Test Data ---

MOCK_VALID_CONFIG_CONTENT = """
{
  "llm": {
    "default": {
      "provider": "openai",
      "model": "gpt-4",
      "api_key": "sk-default_key",
      "base_url": null
    },
    "gpt35": {
      "provider": "openai",
      "model": "gpt-3.5-turbo",
      "api_key": "${OPENAI_API_KEY_GPT35}",
      "base_url": "${OPENAI_BASE_URL}"
    },
    "dummy_required": {
      "provider": "dummy",
      "model": "dummy-model",
      "api_key": null,
      "api_key_required": true
    },
    "dummy_not_required": {
        "provider": "dummy",
        "model": "dummy-nr-model",
        "api_key": null,
        "api_key_required": false
    }
  },
  "mcpServers": {
    "server1": {
      "command": "python",
      "args": ["server1.py"],
      "env": { "VAR1": "value1", "API_KEY": "${MCP_API_KEY}" }
    },
    "server2_disabled": {
      "command": "node",
      "args": ["server2.js"],
      "disabled": true
    }
  },
  "requiredMcpServers": ["server1"]
}
"""

MOCK_INVALID_JSON_CONTENT = "{ invalid json"

MOCK_EXTERNAL_MCP_CONFIG_CONTENT = """
{
  "mcpServers": {
    "external_server": {
        "command": "java",
        "args": ["-jar", "external.jar"],
        "env": {"JAVA_OPTS": "-Xmx512m"}
    },
    "server1": {
        "command": "overridden_python",
        "args": ["overridden_server1.py"]
    }
  }
}
"""


# --- Helper Functions ---

@pytest.fixture(autouse=True)
def clear_env_vars(monkeypatch):
    """Clears relevant env vars before each test."""
    vars_to_clear = [
        "DEFAULT_LLM", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DUMMY_API_KEY",
        "OPENAI_API_KEY_GPT35", "OPENAI_BASE_URL", "MCP_API_KEY",
        "SUPPRESS_DUMMY_KEY", "DISABLE_MCP_MERGE",
        "SWARM_DEBUG", "DEFAULT_LLM_PROVIDER", "DEFAULT_LLM_MODEL"
    ]
    for var in vars_to_clear:
        monkeypatch.delenv(var, raising=False)

@pytest.fixture
def mock_config_file(tmp_path):
    """Creates a temporary mock config file."""
    p = tmp_path / "swarm_config.json"
    p.write_text(MOCK_VALID_CONFIG_CONTENT, encoding='utf-8')
    return p

@pytest.fixture
def mock_external_mcp_file(tmp_path, monkeypatch):
    """Creates a mock external MCP config file."""
    if os.name == "nt":
        appdata = tmp_path / "AppData" / "Roaming"
        monkeypatch.setenv("APPDATA", str(appdata))
        external_dir = appdata / "Claude"
    else:
        home = tmp_path / "home" / "user"
        monkeypatch.setattr(Path, 'home', lambda: home)
        external_dir = home / ".vscode-server" / "data" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings"
    external_dir.mkdir(parents=True, exist_ok=True)
    external_file = external_dir / ("claude_desktop_config.json" if os.name == "nt" else "cline_mcp_settings.json")
    external_file.write_text(MOCK_EXTERNAL_MCP_CONFIG_CONTENT, encoding='utf-8')
    return external_file

# --- Test Cases ---

# 1. resolve_placeholders (Unchanged)
def test_resolve_placeholders_simple(monkeypatch):
    monkeypatch.setenv("MY_VAR", "my_value")
    data = {"key": "Hello ${MY_VAR}!"}
    resolved = resolve_placeholders(data)
    assert resolved == {"key": "Hello my_value!"}

def test_resolve_placeholders_missing_var_full_string(monkeypatch):
    data = {"key": "${MISSING_VAR}"}
    resolved = resolve_placeholders(data)
    assert resolved == {"key": None}

def test_resolve_placeholders_missing_var_partial_string(monkeypatch):
    data = {"key": "Value: ${MISSING_VAR}"}
    resolved = resolve_placeholders(data)
    assert resolved == {"key": "Value: "}

def test_resolve_placeholders_nested(monkeypatch):
    monkeypatch.setenv("NESTED_VAL", "nested")
    monkeypatch.setenv("LIST_VAL", "item2")
    data = {
        "level1": {"key": "${NESTED_VAL}"},
        "list": ["item1", "${LIST_VAL}", {"inner": "${NESTED_VAL}"}]
    }
    resolved = resolve_placeholders(data)
    assert resolved == {
        "level1": {"key": "nested"},
        "list": ["item1", "item2", {"inner": "nested"}]
    }

def test_resolve_placeholders_non_string():
    data = {"int": 123, "bool": True, "null": None, "list": [1, False]}
    resolved = resolve_placeholders(data)
    assert resolved == data


# 2. load_server_config
@patch("pathlib.Path.is_file")
@patch("pathlib.Path.read_text")
def test_load_server_config_success(mock_read_text, mock_is_file, tmp_path, monkeypatch):
    # --- FIX: Use list for side_effect ---
    # The generator `next(...)` stops on the first True, so is_file is called only once.
    mock_is_file.side_effect = [True]
    mock_read_text.return_value = MOCK_VALID_CONFIG_CONTENT
    monkeypatch.setenv("MCP_API_KEY", "mcp_test_key")

    # Mock cwd, BASE_DIR, home to control search order
    monkeypatch.setattr(Path, 'cwd', lambda: tmp_path)
    monkeypatch.setattr("swarm.extensions.config.config_loader.BASE_DIR", tmp_path / "nonexistent_base")
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / "nonexistent_home")

    loaded_config = load_server_config() # Should find it in cwd

    assert loaded_config is not None
    assert loaded_config["llm"]["default"]["model"] == "gpt-4"
    assert loaded_config["mcpServers"]["server1"]["env"]["API_KEY"] == "mcp_test_key"
    mock_read_text.assert_called_once_with(encoding='utf-8')
    # Assert is_file was called once (because next() stops iteration)
    mock_is_file.assert_called_once()


@patch("pathlib.Path.is_file", return_value=False) # Mock all paths don't exist
def test_load_server_config_not_found(mock_is_file, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: Path("/nonexistent/home"))
    monkeypatch.setattr("swarm.extensions.config.config_loader.BASE_DIR", Path("/nonexistent/base"))
    monkeypatch.setattr(Path, 'cwd', lambda: Path("/nonexistent/cwd"))
    with pytest.raises(FileNotFoundError):
        load_server_config()
    # is_file should have been called 3 times (cwd, BASE_DIR, home)
    assert mock_is_file.call_count == 3

@patch("pathlib.Path.is_file")
@patch("pathlib.Path.read_text")
def test_load_server_config_invalid_json(mock_read_text, mock_is_file, tmp_path, monkeypatch):
    # --- FIX: Use list for side_effect ---
    mock_is_file.side_effect = [True] # Found in cwd
    mock_read_text.return_value = MOCK_INVALID_JSON_CONTENT

    # Mock cwd, BASE_DIR, home
    monkeypatch.setattr(Path, 'cwd', lambda: tmp_path)
    monkeypatch.setattr("swarm.extensions.config.config_loader.BASE_DIR", tmp_path / "nonexistent_base")
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / "nonexistent_home")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_server_config()
    # Assert is_file was called once
    mock_is_file.assert_called_once()

@patch("pathlib.Path.is_file")
@patch("pathlib.Path.read_text")
def test_load_server_config_specific_path(mock_read_text, mock_is_file):
    specific_path = "/custom/path/config.json"
    # --- FIX: Use list for side_effect ---
    # This scenario checks the specific path first.
    mock_is_file.side_effect = [True]
    mock_read_text.return_value = MOCK_VALID_CONFIG_CONTENT

    config = load_server_config(file_path=specific_path)
    assert config is not None
    assert config["llm"]["default"]["model"] == "gpt-4"
    # Assert is_file was called once (for the specific path)
    mock_is_file.assert_called_once()
    mock_read_text.assert_called_once_with(encoding='utf-8')


# 3. process_config (includes MCP merge logic) (Unchanged)
def test_process_config_no_merge(monkeypatch):
    monkeypatch.setenv("DISABLE_MCP_MERGE", "true")
    raw_config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    processed = process_config(raw_config.copy())
    assert "external_server" not in processed.get("mcpServers", {})
    assert processed["mcpServers"]["server1"]["command"] == "python"

@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data=MOCK_EXTERNAL_MCP_CONFIG_CONTENT)
def test_process_config_with_merge(mock_file_open, mock_exists, monkeypatch, mock_external_mcp_file):
    monkeypatch.delenv("DISABLE_MCP_MERGE", raising=False)
    mock_exists.return_value = True
    raw_config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    processed = process_config(raw_config.copy())
    assert "external_server" in processed.get("mcpServers", {})
    assert processed["mcpServers"]["external_server"]["command"] == "java"
    assert processed["mcpServers"]["server1"]["command"] == "python"
    assert "server2_disabled" in processed["mcpServers"]


# 4. load_llm_config (Unchanged)
def test_load_llm_config_default(monkeypatch):
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config)
    assert llm_config["model"] == "gpt-4"
    assert llm_config["api_key"] == "sk-default_key"
    assert llm_config["_log_key_source"] == "config file ('default') (resolved)"

def test_load_llm_config_specific_name(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY_GPT35", "env_gpt35_key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://env.openai.com")
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config, llm_name="gpt35")
    assert llm_config["model"] == "gpt-3.5-turbo"
    assert llm_config["api_key"] == "env_gpt35_key"
    assert llm_config["base_url"] == "http://env.openai.com"
    assert llm_config["_log_key_source"] == "config file ('gpt35') (resolved)"

def test_load_llm_config_env_override_specific(monkeypatch):
    monkeypatch.setenv("DUMMY_API_KEY", "env_dummy_specific_key")
    monkeypatch.setenv("OPENAI_API_KEY", "env_openai_fallback_key")
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config, llm_name="dummy_required")
    assert llm_config["model"] == "dummy-model"
    assert llm_config["api_key"] == "env_dummy_specific_key"
    assert llm_config["_log_key_source"] == "env var 'DUMMY_API_KEY'"

def test_load_llm_config_env_override_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env_openai_fallback_key")
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config, llm_name="default")
    assert llm_config["model"] == "gpt-4"
    assert llm_config["api_key"] == "env_openai_fallback_key"
    assert llm_config["_log_key_source"] == "env var 'OPENAI_API_KEY'"


def test_load_llm_config_not_required_no_key(monkeypatch):
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config, llm_name="dummy_not_required")
    assert llm_config["api_key"] is None
    assert llm_config["_log_key_source"] == "Not Required/Not Found"

def test_load_llm_config_profile_not_found_fallback(monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "fallback_provider")
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "fallback_model")
    monkeypatch.setenv("FALLBACK_PROVIDER_API_KEY", "fallback_key_from_env")
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    llm_config = load_llm_config(config, llm_name="nonexistent_profile")
    assert llm_config["provider"] == "fallback_provider"
    assert llm_config["model"] == "fallback_model"
    assert llm_config["api_key"] == "fallback_key_from_env"
    assert llm_config["_log_key_source"] == "env var 'FALLBACK_PROVIDER_API_KEY'"

# 5. get_llm_model (Unchanged)
def test_get_llm_model_success():
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    model = get_llm_model(config, llm_name="default")
    assert model == "gpt-4"

def test_get_llm_model_not_found(monkeypatch):
    config = {"llm": {}}
    model = get_llm_model(config, llm_name="missing")
    assert model == "gpt-4o"

# 6. are_required_mcp_servers_configured <-- Function/Test Removed

# 7. get_server_params (Unchanged)
def test_get_server_params_success(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "mcp_key_123")
    monkeypatch.setenv("OTHER_ENV", "system_value")
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    resolved_config = resolve_placeholders(config)
    server_config = resolved_config["mcpServers"]["server1"]
    params = get_server_params(server_config, "server1")
    assert params is not None
    assert params["command"] == "python"
    assert params["args"] == ["server1.py"]
    assert params["env"]["VAR1"] == "value1"
    assert params["env"]["API_KEY"] == "mcp_key_123"
    assert params["env"]["OTHER_ENV"] == "system_value"
    assert "PWD" in params["env"] or "Path" in params["env"]

def test_get_server_params_missing_command():
    server_config = {"args": [], "env": {}}
    params = get_server_params(server_config, "test_server")
    assert params is None

def test_get_server_params_invalid_args():
    server_config = {"command": "cmd", "args": "not_a_list"}
    params = get_server_params(server_config, "test_server")
    assert params is None

def test_get_server_params_invalid_env():
    server_config = {"command": "cmd", "env": "not_a_dict"}
    params = get_server_params(server_config, "test_server")
    assert params is None

def test_get_server_params_env_value_is_none(monkeypatch):
    server_config = {"command": "cmd", "env": {"KEY_NULL": None, "KEY_STR": "value"}}
    params = get_server_params(server_config, "test_server")
    assert params is not None
    assert "KEY_NULL" not in params["env"]
    assert params["env"]["KEY_STR"] == "value"

# 8. list_mcp_servers (Unchanged)
def test_list_mcp_servers():
    config = json.loads(MOCK_VALID_CONFIG_CONTENT)
    server_list = list_mcp_servers(config)
    assert sorted(server_list) == sorted(["server1", "server2_disabled"])

def test_list_mcp_servers_no_servers():
    config = {"llm": {}}
    server_list = list_mcp_servers(config)
    assert server_list == []

