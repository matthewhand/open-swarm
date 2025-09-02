import os
import sys
from importlib import reload

import pytest


@pytest.mark.integration
def test_geese_cli_main_test_mode(monkeypatch, capsys):
    # Ensure test mode for deterministic CLI output
    monkeypatch.setenv("SWARM_TEST_MODE", "1")

    # Prepare argv for CLI: provide a prompt to avoid interactive input
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    test_prompt = "Tell me a tale"
    monkeypatch.setenv("DEFAULT_LLM", "test")  # ensure no real model resolution

    # Import locally to allow argv patching to take effect
    from swarm.blueprints.geese import geese_cli

    monkeypatch.setenv("PYTHONUNBUFFERED", "1")
    monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    monkeypatch.setenv("DJANGO_TEST_DB_NAME", ":memory:")

    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("COLUMNS", "80")

    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")

    monkeypatch.setattr(sys, "argv", ["geese_cli.py", "--message", test_prompt])

    # Execute main and capture output
    geese_cli.main()
    out, err = capsys.readouterr()

    # Validate spinner outputs and final story line are present
    assert "[SPINNER] Generating." in out
    assert "[SPINNER] Generating.." in out
    assert "[SPINNER] Generating..." in out
    assert "[SPINNER] Running..." in out

    # Geese CLI should print the final assistant message content
    assert "Geese: Once upon a time... (test mode story)." in out
    assert "Geese run complete." in out

