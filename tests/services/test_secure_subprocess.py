from unittest.mock import patch

import pytest
import subprocess
from src.swarm.services.secure_subprocess import (
    execute_command_safe,
    execute_command_with_fallback,
    validate_command_safety,
    sanitize_environment,
    SecureCommandExecutor,
)

def test_execute_command_safe_success():
    res = execute_command_safe(["echo", "hello"])
    assert res.returncode == 0
    assert "hello" in res.stdout

def test_execute_command_safe_string_parsing():
    res = execute_command_safe("echo world")
    assert res.returncode == 0
    assert "world" in res.stdout

def test_execute_command_safe_empty_raises():
    with pytest.raises(ValueError):
        execute_command_safe("")

def test_validate_command_safety():
    assert validate_command_safety(["echo", "safe"]) is True
    assert validate_command_safety(["echo", "test; rm -rf /"]) is False
    assert validate_command_safety(["echo", "a && b"]) is False
    assert validate_command_safety(["rm", "file"]) is False

def test_sanitize_environment():
    env = {"PATH": "/usr/bin:/bin", "LD_PRELOAD": "/malicious.so", "CUSTOM_VAR": "value"}
    clean = sanitize_environment(env)
    assert "LD_PRELOAD" not in clean
    assert clean["CUSTOM_VAR"] == "value"

def test_secure_command_executor():
    executor = SecureCommandExecutor(timeout=10)
    res = executor.execute(["echo", "secure_executor_test"])
    assert res.returncode == 0
    assert executor.get_last_command() == ["echo", "secure_executor_test"]
    assert executor.did_use_fallback() is False


def test_execute_command_with_fallback_never_uses_shell():
    """Parse failures must raise — never re-run via shell=True."""
    with patch("src.swarm.services.secure_subprocess.subprocess.run") as mock_run:
        with pytest.raises(ValueError, match="Invalid command syntax|empty"):
            execute_command_with_fallback("echo 'unclosed")
        mock_run.assert_not_called()


def test_execute_command_with_fallback_success_no_shell_flag():
    with patch("src.swarm.services.secure_subprocess.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "ok"], returncode=0, stdout="ok\n", stderr=""
        )
        result, used_fallback = execute_command_with_fallback(["echo", "ok"])
        assert used_fallback is False
        assert result.returncode == 0
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs.get("shell") is False


def test_secure_executor_rejects_unsafe_without_shell_fallback():
    executor = SecureCommandExecutor()
    with patch("src.swarm.services.secure_subprocess.subprocess.run") as mock_run:
        with pytest.raises(ValueError, match="Unsafe command"):
            executor.execute(["rm", "-rf", "/"])
        mock_run.assert_not_called()
        assert executor.did_use_fallback() is False
