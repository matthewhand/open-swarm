import json
import os
import tempfile
from pathlib import Path

import pytest
from swarm.core import config_loader


def make_temp_config(content):
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(json.dumps(content))
    return Path(path)

def test_load_full_configuration_defaults():
    """Test loading full configuration with defaults and comprehensive validation"""
    config = {
        "defaults": {"foo": "bar", "timeout": 30},
        "llm": {"default": {"provider": "openai", "model": "gpt-3.5", "temperature": 0.7}},
        "mcpServers": {"test": {"command": "run-test", "args": ["--verbose"]}},
        "blueprints": {},
        "profiles": {"custom": {"model": "gpt-4"}}
    }
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path_for_tests=path
    )

    # Comprehensive configuration validation
    assert result["foo"] == "bar", "Default value should be preserved"
    assert result["timeout"] == 30, "Numeric default should be preserved"
    assert "llm" in result, "LLM section should be present"
    assert "mcpServers" in result, "MCP servers section should be present"
    assert "profiles" in result, "Profiles section should be present"

    # LLM configuration validation
    llm_config = result["llm"]
    assert llm_config["default"]["provider"] == "openai", "LLM provider should match"
    assert llm_config["default"]["model"] == "gpt-3.5", "LLM model should match"
    assert llm_config["default"]["temperature"] == 0.7, "LLM temperature should match"

    # MCP server configuration validation
    mcp_config = result["mcpServers"]
    assert mcp_config["test"]["command"] == "run-test", "MCP command should match"
    assert mcp_config["test"]["args"] == ["--verbose"], "MCP args should match"

    # Profiles validation
    profiles_config = result["profiles"]
    assert profiles_config["custom"]["model"] == "gpt-4", "Profile model should match"

    # Validate configuration structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert len(result) >= 4, "Should have at least 4 top-level sections"

def test_load_full_configuration_profile_merging():
    config = {
        "defaults": {"foo": "bar", "default_profile": "special"},
        "llm": {"default": {"provider": "openai"}},
        "mcpServers": {},
        "blueprints": {"FakeBlueprint": {"baz": 123}},
        "profiles": {"special": {"profile_key": "profile_val"}}
    }
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path_for_tests=path  # UPDATED
    )
    assert result["foo"] == "bar"
    assert result["baz"] == 123
    assert result["profile_key"] == "profile_val"

def test_load_full_configuration_env_substitution(monkeypatch):
    monkeypatch.setenv("TEST_ENV_VAR", "replaced-val")
    config = {
        "defaults": {"foo": "$TEST_ENV_VAR"},
        "llm": {}, "mcpServers": {}, "blueprints": {}, "profiles": {}
    }
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path_for_tests=path  # UPDATED
    )
    assert result["foo"] == "replaced-val"

def test_load_full_configuration_missing_file():
    # This test now checks behavior when a config_path_override is given and not found.
    # The XDG default or default_config_path_for_tests not existing is a warning, not an error.
    with pytest.raises(FileNotFoundError):
        config_loader.load_full_configuration(
            blueprint_class_name="FakeBlueprint",
            config_path_override="/tmp/does_not_exist.json" # Ensure this specific override is checked
        )

def test_load_full_configuration_bad_json():
    fd, path_str = tempfile.mkstemp(suffix='.json')
    path = Path(path_str)
    with os.fdopen(fd, 'w') as tmp:
        tmp.write("not a json")
    with pytest.raises(ValueError):
        config_loader.load_full_configuration(
            blueprint_class_name="FakeBlueprint",
            default_config_path_for_tests=path  # UPDATED
        )

def test_load_full_configuration_empty_config():
    config = {}
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path_for_tests=path  # UPDATED
    )
    assert isinstance(result, dict)
    assert "llm" in result
    assert "mcpServers" in result

def test_load_environment(tmp_path, monkeypatch):
    # Temporarily monkeypatch get_project_root_dir to return tmp_path for this test
    # as load_environment now internally calls get_project_root_dir()
    monkeypatch.setattr(config_loader, 'get_project_root_dir', lambda: tmp_path)

    env_file = tmp_path / ".env"
    env_file.write_text("MY_ENV_VAR=hello\n")

    # Clear the env var if it exists from a previous run or environment
    if "MY_ENV_VAR" in os.environ:
        del os.environ["MY_ENV_VAR"]

    config_loader.load_environment() # UPDATED - no arguments
    assert os.environ.get("MY_ENV_VAR") == "hello"

    # Clean up env var after test
    if "MY_ENV_VAR" in os.environ:
        del os.environ["MY_ENV_VAR"]

