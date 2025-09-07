import os
import re
import subprocess
import sys

import pytest


def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@pytest.mark.timeout(15)
def test_geese_cli_story_ux(tmp_path):
    # Run the geese CLI with a story prompt in test mode
    env = os.environ.copy()
    env['SWARM_TEST_MODE'] = '1'
    # Minimal config to avoid config errors
    config_path = tmp_path / "dummy_swarm_config.json"
    env['SWARM_CONFIG_PATH'] = str(config_path)
    config_path.write_text('{"llm": {"default": {"model": "gpt-4o", "provider": "openai", "api_key": "dummy", "base_url": "http://localhost"}}}')
    result = subprocess.run([
        sys.executable, 'src/swarm/blueprints/geese/geese_cli.py', '--message', 'Tell a short story about a goose.'],
        cwd=os.getcwd(),
        capture_output=True, text=True, env=env, timeout=30
    )
    output = strip_ansi(result.stdout + result.stderr)

    # Check for spinner messages (now using [SPINNER] marker for testability)
    assert any(f"[SPINNER] {msg}" in output for msg in [
        'Generating.', 'Generating..', 'Generating...', 'Running...'
    ]), f"Spinner messages not found in output: {output}"

    # Check for multiple spinner updates
    assert output.count('[SPINNER]') >= 2, "Not enough progressive spinner updates"

    # Check for final story output
    assert "Geese:" in output, "Final story output not found"
    assert "Title:" in output, "Story title not found"
    assert "Word Count:" in output, "Story word count not found"

    assert result.returncode == 0
