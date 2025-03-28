import sys
print(f"SYS.PATH during pytest collection/run: {sys.path}") # Keep this for debugging path issues

import pytest
import subprocess
import json
from pathlib import Path
import os
from subprocess import TimeoutExpired # Import TimeoutExpired

# Adjust import based on project structure and pytest execution context
# Attempt direct import assuming PYTHONPATH or pytest finds it
try:
    # If pytest runs from the root, it should find 'blueprints' directly if src/ is effectively added to path
    from blueprints.mcp_demo.blueprint_mcp_demo import MCPDemoBlueprint
except ModuleNotFoundError:
    print("ModuleNotFoundError caught in test file import. Check sys.path and project structure.")
    # This path issue seems deeper, as the blueprint itself fails to import 'agents'
    raise # Re-raise to see the original error trace

# Define the path to the blueprint script
BLUEPRINT_PATH = Path(__file__).parent.parent.parent / "blueprints" / "mcp_demo" / "blueprint_mcp_demo.py"
# Ensure the path is absolute
BLUEPRINT_SCRIPT = str(BLUEPRINT_PATH.resolve())
# Define a timeout for subprocess calls (in seconds)
SUBPROCESS_TIMEOUT = 10 # Set timeout to 10 seconds

# --- Test Fixtures (if any, e.g., for setup/teardown) ---
# (None needed for these basic CLI tests yet)

# --- Test Functions ---

@pytest.mark.cli
def test_mcp_demo_cli_help():
    """Test running the blueprint script with --help flag."""
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--help"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=SUBPROCESS_TIMEOUT) # Use 10s timeout
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for --help command.")

    # Help usually exits with 0, but check just in case argparse changes behavior
    # assert result.returncode == 0
    assert "usage: blueprint_mcp_demo.py" in result.stdout
    # Check for the CORRECT argument used by BlueprintBase.main()
    assert "--instruction" in result.stdout
    assert "--config" in result.stdout
    assert "--debug" in result.stdout

@pytest.mark.cli
def test_mcp_demo_cli_simple_task():
    """Test running the blueprint script with a simple task (no tools)."""
    instruction = "Say hello"
    # Command: uv run python ... --instruction "Say hello"
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT) # Use 10s timeout
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for simple task.")

    assert result.returncode == 0
    # Check for assistant response in stdout (might vary slightly)
    assert "Hello" in result.stdout or "Hi" in result.stdout

@pytest.mark.cli
@pytest.mark.tools
def test_mcp_demo_cli_time(capsys):
    """Test running the blueprint script asking for the time (should trigger get_current_time tool)."""
    instruction = "What time is it?"
    # Command: uv run python ... --instruction "What time is it?" --debug
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT) # Use 10s timeout
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for time task.")

    assert result.returncode == 0

    # Check stderr for debug logs indicating tool use
    stderr_output = result.stderr
    print("\nSUBPROCESS STDERR:")
    print(stderr_output)
    print("\nSUBPROCESS STDOUT:")
    print(result.stdout)

    # Check for agent/tool activity logs (exact messages might change)
    assert "Using profile 'gpt-4o'" in stderr_output # Check if agent client setup happened
    assert "Executing get_current_time tool" in stderr_output # Check the log message from the tool
    # Check stdout for a plausible time-like response (ISO format has T)
    assert "T" in result.stdout
    assert ":" in result.stdout


@pytest.mark.cli
@pytest.mark.tools
@pytest.mark.agents
def test_mcp_demo_cli_list_files(capsys):
    """Test running the blueprint script asking to list files (should trigger Explorer agent -> list_files tool)."""
    instruction = "List files in ."
    # Command: uv run python ... --instruction "List files in ." --debug
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT) # Use 10s timeout
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for list files task.")


    assert result.returncode == 0

    # Check stderr for debug logs
    stderr_output = result.stderr
    print("\nSUBPROCESS STDERR:")
    print(stderr_output)
    print("\nSUBPROCESS STDOUT:")
    print(result.stdout)

    assert "Agent Sage now uses Explorer as a tool." in stderr_output # Check blueprint setup log
    # Check if Sage called the Explorer tool (Log message might vary based on agents lib implementation)
    assert "Tool call requested for Explorer" in stderr_output or "Calling tool Explorer" in stderr_output # Adjust based on actual logs
    assert "Executing list_files tool with path: ." in stderr_output # Check if Explorer called the function tool
    # Check stdout for a file known to be in that directory (e.g., the blueprint script itself)
    assert "blueprint_mcp_demo.py" in result.stdout

# Add more tests as needed
