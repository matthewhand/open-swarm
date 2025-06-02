import subprocess
import re
import sys
import os
import pytest

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@pytest.mark.skip(reason="GeeseBlueprint functionality changed; CLI test needs review for story output vs search UX.")
@pytest.mark.timeout(15)
def test_geese_cli_search_ux(tmp_path):
    # Create a dummy file structure to search
    (tmp_path / "foo.py").write_text("print('hello world')\n")
    (tmp_path / "bar.txt").write_text("not python\n")
    # Run the geese CLI with a search prompt targeting the temp dir
    env = os.environ.copy()
    env['SWARM_CONFIG_PATH'] = str(tmp_path / "dummy_swarm_config.json")
    env['SWARM_TEST_MODE'] = '1'
    # Minimal config to avoid config errors
    (tmp_path / "dummy_swarm_config.json").write_text('{"llm": {"default": {"model": "gpt-4o", "provider": "openai", "api_key": "dummy", "base_url": "http://localhost"}}}')
    result = subprocess.run([
        sys.executable, 'src/swarm/blueprints/geese/geese_cli.py', '--message', 'Find *.py files'],
        cwd=os.getcwd(),
        capture_output=True, text=True, env=env, timeout=30
    )
    output = strip_ansi(result.stdout + result.stderr)

    # Check for spinner messages (now using [SPINNER] marker for testability)
    assert any(f"[SPINNER] {msg}" in output for msg in [
        'Generating.', 'Generating..', 'Generating...', 'Running...'
    ]), f"Spinner messages not found in output: {output}"

    # Check for operation box with emoji and title
    assert '╭' in output and '╰' in output, "Box borders not found"
    assert '🔍' in output or '💡' in output, "Expected emoji not found"
    assert 'Searching Filesystem' in output or 'Geese Output' in output, "Expected box title not found"

    # Check for result count/progress
    match = re.search(r'Matches so far: ?\d+', output)
    if not match:
        print('--- CLI OUTPUT FOR DEBUGGING ---')
        print(output)
    assert match, "Result count not found"

    # Optionally: check for progressive updates (multiple boxes or lines)
    assert output.count('╭') > 1, "No progressive updates detected"

    assert result.returncode == 0
