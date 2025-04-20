import os
import subprocess

def test_zeus_cli_integration():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    result = subprocess.run(
        ['python3', 'src/swarm/blueprints/zeus/zeus_cli.py', '--message', 'Who is the king of the gods?'],
        capture_output=True, text=True, env=env
    )
    # Output should indicate Zeus agent/LLM operation
    assert ("Zeus" in result.stdout or "pantheon" in result.stdout or "god" in result.stdout), f"Unexpected output: {result.stdout}"
    assert result.returncode == 0
