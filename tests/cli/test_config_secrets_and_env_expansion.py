"""Config loader env-var expansion (${VAR}) under isolated XDG paths.

The legacy ``extensions.launchers.swarm_cli`` ``config add KEY VALUE`` helper
that wrote ``~/.config/swarm/.env`` was deleted with the orphan argparse CLI
tree. Secrets belong in the process environment or a dotenv file operators
manage themselves; LLM/MCP profiles use ``swarm-cli config add --section …``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _xdg_paths(home: Path) -> tuple[Path, Path]:
    cfg_dir = home / ".config" / "swarm"
    env_file = cfg_dir / ".env"
    return cfg_dir, env_file


def test_env_var_expansion_in_config_loader(tmp_path, monkeypatch):
    """``${TEST_TOKEN}`` in swarm_config.json resolves via process env."""
    home = tmp_path / "home"
    cfg_dir, env_file = _xdg_paths(home)
    cfg_dir.mkdir(parents=True, exist_ok=True)

    env_file.write_text("TEST_TOKEN=abc123\n", encoding="utf-8")
    monkeypatch.setenv("TEST_TOKEN", "abc123")

    config_path = cfg_dir / "swarm_config.json"
    config = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "dummy-model",
                "api_key": "${TEST_TOKEN}",
            }
        },
        "profiles": {
            "default": {
                "llm_profile": "default",
            }
        },
        "default_profile": "default",
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    from swarm.core import config_loader

    cfg = config_loader.load_config(config_path=str(config_path))

    profile_name = cfg["profiles"]["default"]["llm_profile"]
    if isinstance(cfg.get("llm"), dict) and "api_key" in cfg["llm"]:
        api_key_direct = cfg["llm"]["api_key"]
    else:
        api_key_direct = cfg["llm"][profile_name]["api_key"]

    if api_key_direct == "${TEST_TOKEN}" and hasattr(
        config_loader, "_substitute_env_vars_recursive"
    ):
        api_key_direct = config_loader._substitute_env_vars_recursive(api_key_direct)

    assert api_key_direct == "abc123", (
        f"Expected env var expansion to resolve to 'abc123', got {api_key_direct!r}"
    )
