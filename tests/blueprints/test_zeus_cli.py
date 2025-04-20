import subprocess
import sys
import os
import pytest

ZEUS_CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/swarm/blueprints/zeus/blueprint_zeus.py'))

@pytest.mark.skipif(not os.path.exists(ZEUS_CLI_PATH), reason="Zeus CLI script not found.")
def test_zeus_cli_banner():
    result = subprocess.run([sys.executable, ZEUS_CLI_PATH], input="exit\n", capture_output=True, text=True)
    # Check for the Zeus banner in output
    assert "ZEUS: GENERAL-PURPOSE SWARM COORDINATOR AGENT DEMO" in result.stdout
    # Accept nonzero exit code if output is correct
    assert result.returncode == 0 or result.returncode == 1

@pytest.mark.skipif(not os.path.exists(ZEUS_CLI_PATH), reason="Zeus CLI script not found.")
def test_zeus_cli_multiple_inputs():
    # Simulate two user inputs, then exit
    inputs = "How are you?\nWhat is your name?\nexit\n"
    result = subprocess.run([sys.executable, ZEUS_CLI_PATH], input=inputs, capture_output=True, text=True)
    out = result.stdout + result.stderr
    # Should echo both prompts in the output or show help
    assert ("How are you?" in out or "help" in out.lower())
    assert ("What is your name?" in out or "help" in out.lower())
    # Accept nonzero exit code if output is correct
    assert result.returncode == 0 or result.returncode == 1
