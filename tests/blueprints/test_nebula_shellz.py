import pytest
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired

# Define the path to the blueprint script
BLUEPRINT_PATH = Path(__file__).parent.parent.parent / "blueprints" / "nebula_shellz" / "blueprint_nebula_shellz.py"
BLUEPRINT_SCRIPT = str(BLUEPRINT_PATH.resolve())
SUBPROCESS_TIMEOUT = 25 # Slightly longer timeout for agent interactions

@pytest.mark.cli
def test_nebula_shellz_cli_simple_task():
    """Test running nebula_shellz with a simple task."""
    instruction = "Who leads the Nebuchadnezzar crew?"
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT)
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for simple task.")
    except subprocess.CalledProcessError as e:
         print("\nSTDOUT:")
         print(e.stdout)
         print("\nSTDERR:")
         print(e.stderr)
         pytest.fail(f"Subprocess failed with exit code {e.returncode}")


    assert result.returncode == 0
    # Check stdout for a plausible response from Morpheus
    print("\nSTDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    # Morpheus should identify himself or mention leadership
    assert "Morpheus" in result.stdout or "leader" in result.stdout or "lead the crew" in result.stdout

@pytest.mark.cli
@pytest.mark.tools
def test_nebula_shellz_cli_shell_command():
    """Test running nebula_shellz asking Morpheus to execute a simple shell command directly."""
    instruction = "Morpheus, please use execute_shell_command to run 'echo hello nebula'"
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT)
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds for shell command task.")
    except subprocess.CalledProcessError as e:
         print("\nSTDOUT:")
         print(e.stdout)
         print("\nSTDERR:")
         print(e.stderr)
         pytest.fail(f"Subprocess failed with exit code {e.returncode}")

    assert result.returncode == 0
    print("\nSTDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    # Check for logs indicating the tool was called by Morpheus
    assert "Executing shell command: echo hello nebula" in result.stderr
    # Check for the expected output in the final response
    assert "hello nebula" in result.stdout

@pytest.mark.cli
@pytest.mark.tools
@pytest.mark.agents # Mark as agent interaction test
def test_nebula_shellz_cli_delegate_shell( ):
    """Test running nebula_shellz asking Morpheus to delegate shell command execution to Tank."""
    instruction = "Morpheus, please ask Tank to execute the shell command 'pwd'"
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT + 10) # Longer timeout for delegation
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT + 10} seconds for delegated shell command task.")
    except subprocess.CalledProcessError as e:
         print("\nSTDOUT:")
         print(e.stdout)
         print("\nSTDERR:")
         print(e.stderr)
         pytest.fail(f"Subprocess failed with exit code {e.returncode}")

    assert result.returncode == 0
    print("\nSTDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    # Check for logs indicating delegation occurred (Morpheus calling Tank tool)
    assert "Calling tool Tank" in result.stderr or "Tool call requested for Tank" in result.stderr
    # Check for logs indicating Tank executed the command
    assert "Executing shell command: pwd" in result.stderr
    # Check for the expected output (current directory, likely /mnt/models/open-swarm-mcp)
    assert "/mnt/models/open-swarm-mcp" in result.stdout

