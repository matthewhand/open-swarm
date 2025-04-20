import os
import subprocess
import pytest

def test_zeus_binary():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    binary = './dist/zeus_cli'
    if not os.path.exists(binary):
        pytest.skip(f"Binary {binary} not found. Build with: pyinstaller --onefile src/swarm/blueprints/zeus/zeus_cli.py --name zeus_cli")
    result = subprocess.run([binary, '--message', 'Break down the task: Build a REST API for a todo app, and assign subtasks to the appropriate gods.'], capture_output=True, text=True, env=env)
    assert ("Zeus" in result.stdout or "pantheon" in result.stdout or "Odin" in result.stdout)
    assert result.returncode == 0
