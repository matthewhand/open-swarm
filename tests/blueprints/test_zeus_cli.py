import subprocess
import sys
from pathlib import Path

import pytest

# Correctly determine project root and then path to blueprint_zeus.py
# Assuming this test file is at tests/blueprints/test_zeus_cli.py
# Project root is two levels up from this file's directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ZEUS_CLI_PATH = PROJECT_ROOT / "src/swarm/blueprints/zeus/blueprint_zeus.py"

@pytest.mark.skipif(not ZEUS_CLI_PATH.is_file(), reason=f"Zeus CLI script not found at {ZEUS_CLI_PATH}")
def test_zeus_cli_banner():
    result = subprocess.run([sys.executable, str(ZEUS_CLI_PATH)], input="exit\n", capture_output=True, text=True, timeout=20) # Increased timeout
    # The __main__ in blueprint_zeus.py prints "\033[1;36m\nZeus CLI Demo\033[0m"
    # ANSI codes might be present or stripped by subprocess depending on TTY.
    # We'll check for the core text.
    assert "Zeus CLI Demo" in result.stdout or "Zeus CLI Demo" in result.stderr, \
        f"Banner 'Zeus CLI Demo' not found. STDOUT: {result.stdout} STDERR: {result.stderr}"

@pytest.mark.skipif(not ZEUS_CLI_PATH.is_file(), reason=f"Zeus CLI script not found at {ZEUS_CLI_PATH}")
def test_zeus_cli_multiple_inputs():
    inputs = "How are you?\nWhat is your name?\nexit\n"
    result = subprocess.run([sys.executable, str(ZEUS_CLI_PATH)], input=inputs, capture_output=True, text=True, timeout=30) # Increased timeout
    out = result.stdout + result.stderr

    assert "Zeus CLI Demo" in out, f"Initial CLI demo banner missing. Output: {out}"
    # The __main__ block runs with debug=True, so it yields initial spinner, then raw agent output.
    # The agent is the full Zeus agent, which will try to use OpenAI.
    # For a CLI test, this is complex. We expect at least the spinner.
    # The actual agent output might be an error if OPENAI_API_KEY is not set or is 'sk-test'.
    # A more robust check would be for the spinner and then any subsequent message.
    assert "Generating." in out, f"Expected 'Generating.' spinner message. Output: {out}"
    # Check that some form of agent processing or error occurred after the spinner
    assert "Demo complete." in out, f"Expected 'Demo complete.'. Output: {out}"
    # If OPENAI_API_KEY is 'sk-test', it will likely error out or give a canned response.
    # This test primarily ensures the CLI script runs and processes some input.
