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
