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
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = strip_ansi(result.stdout + result.stderr)

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
