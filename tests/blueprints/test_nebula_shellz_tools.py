import platform

import pytest

# Import the shell execution tool directly for unit testing
from swarm.blueprints.nebula_shellz.blueprint_nebula_shellz import (
    _execute_shell_command_raw as execute_shell_command,
)


def test_execute_shell_command_empty_returns_error():
    out = execute_shell_command("")
    assert isinstance(out, str)
    assert "Error: No command provided." in out


def test_execute_shell_command_basic_echo():
    cmd = "echo hello-world"
    out = execute_shell_command(cmd)
    # Successful exit code and stdout contains expected text
    assert "Exit Code: 0" in out
    assert "STDOUT:\nhello-world" in out


@pytest.mark.skipif(platform.system() == "Windows", reason="Non-existent command semantics differ on Windows")
def test_execute_shell_command_not_found():
    out = execute_shell_command("definitely_not_a_real_binary_12345")
    # Should produce a clear error indicating command not found
    assert "Error: Command not found" in out or "Exit Code:" in out


@pytest.mark.skipif(platform.system() == "Windows", reason="sleep not available by default on Windows")
def test_execute_shell_command_timeout(monkeypatch):
    # Force a very small timeout and run a slow command to trigger timeout
    monkeypatch.setenv("SWARM_COMMAND_TIMEOUT", "1")
    out = execute_shell_command("sleep 2")
    assert "timed out" in out.lower()
