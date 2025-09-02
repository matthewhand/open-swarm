import os
import re
import pytest


# Target the internal helper and class for reliable unit coverage
from src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
    _execute_shell_command_raw,
    NebuchaShellzzarBlueprint,
)


def test_shell_command_raw_empty_returns_error():
    out = _execute_shell_command_raw("")
    assert "Error: No command provided" in out


def test_shell_command_raw_echo_outputs_and_exitcode_zero():
    out = _execute_shell_command_raw("echo hello-world")
    # Normalizes multi-line output structure
    assert "Exit Code: 0" in out
    assert "STDOUT:\nhello-world" in out
    # STDERR should be present but typically empty
    assert "STDERR:" in out


def test_model_instance_missing_profile_raises(monkeypatch):
    # Ensure no env config accidentally satisfies profile resolution
    for key in [
        "OPENAI_API_KEY",
        "LITELLM_API_KEY",
        "OPENAI_BASE_URL",
        "LITELLM_BASE_URL",
        "DEFAULT_LLM",
        "LITELLM_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Make sure no local swarm_config.json is implicitly found by base loader
    monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent-xdg-config")

    bp = NebuchaShellzzarBlueprint(blueprint_id="test-nshell")
    with pytest.raises(ValueError) as excinfo:
        bp._get_model_instance("default")
    # Accept either failure mode depending on code path
    msg = str(excinfo.value)
    assert (
        "Missing LLM profile configuration" in msg
        or "No OPENAI_API_KEY found and config not loaded" in msg
    )


def test_display_splash_screen_no_animation_does_not_raise():
    bp = NebuchaShellzzarBlueprint(blueprint_id="test-nshell")
    # Should not raise and should write to console; we don't assert rich output here
    bp.display_splash_screen(animated=False)
