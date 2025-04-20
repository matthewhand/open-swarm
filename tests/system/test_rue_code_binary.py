import os
import subprocess
import pytest

def test_rue_code_binary():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    binary = './dist/rue_code_cli'
    if not os.path.exists(binary):
        pytest.skip(f"Binary {binary} not found. Build with: pyinstaller --onefile src/swarm/blueprints/rue_code/rue_code_cli.py --name rue_code_cli")
    result = subprocess.run([binary, '--message', 'Estimate the OpenAI API token cost for 1000 tokens'], capture_output=True, text=True, env=env)
    assert "Estimated cost" in result.stdout
    assert result.returncode == 0
