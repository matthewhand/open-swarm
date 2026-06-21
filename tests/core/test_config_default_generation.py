"""Behavioral test for config_loader.create_default_config().

Previously this test was gated behind ``if not found:`` and swallowed exceptions,
so it could pass while asserting nothing. create_default_config is not covered
elsewhere (test_config_discovery / test_find_config_precedence only cover
find_config_file lookup), so this now asserts its real contract unconditionally:
it creates any missing parent dirs and writes a loadable, well-formed default
config containing the default LLM profile.
"""
import json

from swarm.core import config_loader


def test_create_default_config_writes_loadable_default(tmp_path):
    # parent "swarm/" dir intentionally does not exist yet
    config_path = tmp_path / "swarm" / config_loader.DEFAULT_CONFIG_FILENAME
    assert not config_path.exists()

    config_loader.create_default_config(config_path)

    # file (and its parent dir) were created
    assert config_path.exists()

    # contents are valid JSON and carry the documented default LLM profile
    data = json.loads(config_path.read_text())
    assert isinstance(data, dict)
    assert "llm" in data
    assert "default" in data["llm"]
    assert data["llm"]["default"]["provider"] == "openai"
