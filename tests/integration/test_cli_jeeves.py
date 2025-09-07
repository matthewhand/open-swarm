import pytest
import os
import sys
import subprocess
import re # For strip_ansi

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.timeout(15)
def test_jeeves_cli_ux():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    env['SWARM_TEST_MODE'] = '1'
    cmd = [sys.executable, 'src/swarm/blueprints/jeeves/jeeves_cli.py', '--instruction', 'Search for all TODOs in the repo']
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    output = strip_ansi(result.stdout + result.stderr)
    
    # Verify the test handles TODO search instruction by checking for TODO-related output
    assert "TODO" in output, f"Expected TODO mentions in output for search instruction, but found: {output[:200]}..."
    assert result.returncode == 0, f"CLI execution failed with return code {result.returncode}"

    # Check for spinner messages (must match Jeeves SPINNER_STATES)
    # The initial "[SPINNER] Polishing the silver" is printed by JeevesSpinner.start()
    # Subsequent spinner states might be part of the box output from JeevesBlueprint.run() in test mode
    assert "[SPINNER] Polishing the silver" in output, f"Initial spinner message not found in output: {output}"
    
    # Check for subsequent spinner states that JeevesBlueprint.run() might print in its boxes
    # These are not prefixed with [SPINNER] but are part of the box content.
    assert "Generating." in output or "Generating.." in output or "Generating..." in output or "Running..." in output, \
        f"Subsequent spinner states not found in box output: {output}"

    # Check for operation box with emoji and title
    assert '╭' in output and '╰' in output, "Box borders not found"
    # Jeeves CLI in test mode uses '🤖' for its boxes
    assert '🤖' in output, f"Expected emoji '🤖' not found in output: {output}"
    
    # Additional assertion for TODO handling: check if search results or processing is indicated
    # In test mode, Jeeves should process the search instruction and show results or processing steps
    assert any(keyword in output for keyword in ["search", "TODO", "found", "results", "processing"]) or "Jeeves Results" in output, \
        f"Expected evidence of TODO search handling in output: {output[:200]}..."
