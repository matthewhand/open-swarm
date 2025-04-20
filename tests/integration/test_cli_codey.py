import subprocess
import shlex
import sys
import os
import pytest
import re

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.timeout(15)
def test_codey_cli_ux():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    env['SWARM_TEST_MODE'] = '1'
    cmd = [sys.executable, 'src/swarm/blueprints/codey/codey_cli.py', '--message', 'Refactor this function to be async: def foo(x): return x + 1']
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = strip_ansi(result.stdout + result.stderr)

    # Check for spinner messages
    assert any(f"[SPINNER] {msg}" in output for msg in [
        'Generating.', 'Generating..', 'Generating...', 'Running...'
    ]), f"Spinner messages not found in output: {output}"

    # Check for operation box with emoji and title
    assert '╭' in output and '╰' in output, "Box borders not found"
    assert '🔍' in output or '💡' in output or '💻' in output, "Expected emoji not found"
    assert 'Assist' in output or 'Code Search' in output or 'Codey Output' in output, "Expected box title not found"

    # Check for result count/progress
    match = re.search(r'Matches so far: ?\d+', output)
    if not match:
        print('--- CLI OUTPUT FOR DEBUGGING ---')
        print(output)
    assert match, "Result count not found"

    # Optionally: check for progressive updates (multiple boxes or lines)
    assert output.count('╭') > 1, "No progressive updates detected"

    assert result.returncode == 0
