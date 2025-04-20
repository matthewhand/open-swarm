import os
import subprocess
import pytest

def test_codey_binary():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    binary = './dist/codey_cli'
    if not os.path.exists(binary):
        pytest.skip(f"Binary {binary} not found. Build with: pyinstaller --onefile src/swarm/blueprints/codey/codey_cli.py --name codey_cli")
    result = subprocess.run([binary, '--message', 'Suggest a safe refactor for this function: def foo(x): return x + 1'], capture_output=True, text=True, env=env)
    assert ("Proposed code change" in result.stdout or "Approval" in result.stdout or "refactor" in result.stdout)
    assert result.returncode == 0
