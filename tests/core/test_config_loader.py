import os
import tempfile
import json
import pytest
from pathlib import Path
from swarm.core import config_loader

def make_temp_config(content):
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(json.dumps(content))
    return Path(path)

def test_load_full_configuration_defaults():
    config = {
        "defaults": {"foo": "bar"},
        "llm": {"default": {"provider": "openai", "model": "gpt-3.5"}},
        "mcpServers": {"test": {"command": "run-test"}},
        "blueprints": {},
        "profiles": {}
    }
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path=path
    )
    assert result["foo"] == "bar"
    assert "llm" in result
    assert "mcpServers" in result
    assert result["llm"]["default"]["provider"] == "openai"
    assert result["mcpServers"]["test"]["command"] == "run-test"

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
        default_config_path=path
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
        default_config_path=path
    )
    assert result["foo"] == "replaced-val"

def test_load_full_configuration_missing_file():
    with pytest.raises(FileNotFoundError):
        config_loader.load_full_configuration(
            blueprint_class_name="FakeBlueprint",
            default_config_path=Path("/tmp/does_not_exist.json"),
            config_path_override="/tmp/does_not_exist.json"
        )

def test_load_full_configuration_bad_json():
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write("not a json")
    with pytest.raises(ValueError):
        config_loader.load_full_configuration(
            blueprint_class_name="FakeBlueprint",
            default_config_path=Path(path)
        )

def test_load_full_configuration_empty_config():
    config = {}
    path = make_temp_config(config)
    result = config_loader.load_full_configuration(
        blueprint_class_name="FakeBlueprint",
        default_config_path=path
    )
    assert isinstance(result, dict)
    assert "llm" in result
    assert "mcpServers" in result

def test_load_environment(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("MY_ENV_VAR=hello\n")
    config_loader.load_environment(tmp_path)
    assert os.environ.get("MY_ENV_VAR") == "hello"
