import os
import subprocess
import pytest

def test_whinge_binary():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    binary = './dist/whinge'
    if not os.path.exists(binary):
        pytest.skip(f"Binary {binary} not found. Build with: pyinstaller --onefile src/swarm/blueprints/whinge_surf/whinge_surf_cli.py --name whinge")
    result = subprocess.run([binary, '--run', 'python3 -c "print(\'AI job started\')"'], capture_output=True, text=True, env=env)
    assert "Launched subprocess" in result.stdout or "INFO" in result.stdout
    assert result.returncode == 0
