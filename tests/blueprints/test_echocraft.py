import pytest
import subprocess
import pytest
from pathlib import Path
from subprocess import TimeoutExpired

# Define the path to the blueprint script
BLUEPRINT_PATH = Path(__file__).parent.parent.parent / "blueprints" / "echocraft" / "blueprint_echocraft.py"
BLUEPRINT_SCRIPT = str(BLUEPRINT_PATH.resolve())
SUBPROCESS_TIMEOUT = 15 # Should be quick

@pytest.mark.cli
@pytest.mark.tools # As it uses the echo_function tool
@pytest.mark.skip(reason='CLI tests require more setup/mocking')
def test_echocraft_cli_echo():
    """Test running echocraft directly and check echo output."""
    instruction = "Hello EchoCraft!"
    command = ["uv", "run", "python", BLUEPRINT_SCRIPT, "--instruction", instruction, "--debug"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT)
    except TimeoutExpired:
        pytest.fail(f"Subprocess timed out after {SUBPROCESS_TIMEOUT} seconds.")
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
    # Check stderr for tool execution log
    assert "Executing echo_function tool" in result.stderr
    # Check stdout for the exact echoed instruction in the final output section
    assert f"--- Final Output ---\n{instruction}" in result.stdout

