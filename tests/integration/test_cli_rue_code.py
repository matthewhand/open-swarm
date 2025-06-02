import pytest
import os
import sys
import subprocess
import re

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def test_rue_cli_token_cost():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test' # Use a test LLM to avoid actual API calls
    result = subprocess.run(
        ['python3', 'src/swarm/blueprints/rue_code/rue_code_cli.py', '--message', 'What is the cost of this code? def foo(): pass'],
        capture_output=True, text=True, env=env
    )
    output = strip_ansi(result.stdout + result.stderr)
    # Check for cost estimation in output
    assert "Estimated cost" in output
    assert "$" in output

def test_rue_cli_ux():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    result = subprocess.run(
        ['python3', 'src/swarm/blueprints/rue_code/rue_code_cli.py', '--message', 'Summarize this code: def foo(x): return x + 1'],
        capture_output=True, text=True, env=env
    )
    output = strip_ansi(result.stdout + result.stderr)
    # Check for spinner messages (these are not prefixed with [SPINNER] by rue_code_cli's current test mode output)
    assert any(msg in output for msg in [
        'Generating.', 'Generating..', 'Generating...', 'Running...'
    ]), f"Spinner messages not found in output: {output}"
    
    # Check for operation box with emoji and title
    assert '╭' in output and '╰' in output, "Box borders not found"
    # Rue code CLI uses 📝 for its boxes and 🦆 for its final summary banner
    assert '📝' in output or '🦆' in output, f"Expected emoji '📝' or '🦆' not found in output: {output}"
    assert "RueCode Code Results" in output or "RueCode Semantic Results" in output or "RueCode Summary" in output
