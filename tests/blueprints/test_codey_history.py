import pytest
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint
import os
import tempfile

def test_session_logging_and_history(tmp_path):
    blueprint = CodeyBlueprint(blueprint_id="test-logging")
    # Set up a dummy session logger path
    log_dir = tmp_path / "session_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    blueprint.start_session_logger("codey", global_instructions="Test global", project_instructions="Test project", log_dir=log_dir)
    blueprint.log_message("user", "Hello!")
    blueprint.log_message("assistant", "Hi there!")
    blueprint.log_tool_call("search", "Found 2 results")
    blueprint.close_session_logger()
    # Check that a session log file was created
    logs = list(log_dir.glob("*.md"))
    assert logs, "No session log file found"
    with open(logs[0], "r") as f:
        content = f.read()
        assert "Hello!" in content
        assert "Hi there!" in content
        assert "Found 2 results" in content

def test_history_overlay_and_view():
    blueprint = CodeyBlueprint(blueprint_id="test-history-overlay")
    # Simulate session logs
    # (In real implementation, this would call a CLI or overlay function)
    # For now, just check method exists and returns expected type
    assert hasattr(blueprint, "get_approval_policy")
    assert callable(blueprint.get_approval_policy)
    assert blueprint.get_approval_policy() in ("suggest", "auto-edit", "full-auto")

def test_full_context_mode(tmp_path):
    blueprint = CodeyBlueprint(blueprint_id="test-full-context")
    # Simulate full-context flag
    # For now, just ensure the attribute/method exists
    assert hasattr(blueprint, "_inject_context")
    # Simulate a context injection call
    messages = [{"role": "user", "content": "Refactor project"}]
    blueprint._inject_context(messages)
    # No exception means pass for now
