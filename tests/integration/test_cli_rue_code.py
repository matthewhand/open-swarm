import os
import re
import subprocess

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def test_rue_cli_token_cost():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    result = subprocess.run(
        ['python3', 'src/swarm/blueprints/rue_code/rue_code_cli.py', '--message', 'Summarize this code: def foo(x): return x + 1'],
        capture_output=True, text=True, env=env
    )
    # Find the cost line
    match = re.search(r"Estimated cost for .*: \$(\d+\.\d+)", result.stdout)
    assert match, f"Cost line not found in output: {result.stdout}"
    cost = float(match.group(1))
    assert cost > 0, f"Cost should be greater than zero, got {cost}"
    assert result.returncode == 0

def test_rue_cli_ux():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    result = subprocess.run(
        ['python3', 'src/swarm/blueprints/rue_code/rue_code_cli.py', '--message', 'Summarize this code: def foo(x): return x + 1'],
        capture_output=True, text=True, env=env
    )
    output = strip_ansi(result.stdout + result.stderr)
    # Check for spinner messages
    assert any(msg in output for msg in [
        'Generating.', 'Generating..', 'Generating...', 'Running...'
    ]), f"Spinner messages not found in output: {output}"
    # Check for operation box with emoji and title
    assert '╭' in output and '╰' in output, "Box borders not found"
    assert '🔍' in output or '💡' in output or '🧠' in output, "Expected emoji not found"
    assert 'RueCode Output' in output or 'Progressive Operation' in output, "Expected box title not found"
    # Check for result count/progress
    match = re.search(r'Results: ?\d+', output)
    if not match:
        print('--- CLI OUTPUT FOR DEBUGGING ---')
        print(output)
    assert match, "Result count not found"
    # Optionally: check for progressive updates (multiple boxes or lines)
    assert output.count('╭') > 1, "No progressive updates detected"
    assert result.returncode == 0
