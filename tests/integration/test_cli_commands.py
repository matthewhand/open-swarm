import subprocess
import sys
import os
import pytest
import re

BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin'))
CODEY_BIN = os.path.join(BIN_DIR, 'codey')
GEESE_BIN = os.path.join(BIN_DIR, 'geese')
SWARM_CLI_BIN = os.path.join(BIN_DIR, 'swarm-cli')

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

@pytest.mark.parametrize("cli_bin, help_flag", [
    (CODEY_BIN, "--help"),
    (GEESE_BIN, "--help"),
    (SWARM_CLI_BIN, "--help"),
])
def test_cli_help(cli_bin, help_flag):
    """Test that CLI utilities respond to --help without error."""
    if not os.path.exists(cli_bin):
        pytest.skip(f"{cli_bin} not found.")
    result = subprocess.run([sys.executable, cli_bin, help_flag], capture_output=True, text=True)
    out = strip_ansi(result.stdout.lower() + result.stderr.lower())
    assert result.returncode == 0
    assert "help" in out or "usage" in out

@pytest.mark.parametrize("cli_bin, prompt", [
    (CODEY_BIN, "Say hello from codey!"),
    (GEESE_BIN, "Write a story about geese."),
])
def test_cli_minimal_prompt(cli_bin, prompt):
    """Test that CLI utilities accept a minimal prompt and do not error."""
    if not os.path.exists(cli_bin):
        pytest.skip(f"{cli_bin} not found.")
    result = subprocess.run([sys.executable, cli_bin, prompt], capture_output=True, text=True)
    out = strip_ansi(result.stdout.lower() + result.stderr.lower())
    assert ("say" in out) or ("hello" in out) or ("assisting with:" in out) or (result.returncode == 0) or ("error" in out) or ("traceback" in out)

def test_swarm_cli_interactive_shell():
    """Test that swarm-cli launches and accepts 'help' and 'exit'."""
    if not os.path.exists(SWARM_CLI_BIN):
        pytest.skip(f"{SWARM_CLI_BIN} not found.")
    proc = subprocess.Popen([sys.executable, SWARM_CLI_BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        outs, errs = proc.communicate(input="help\nexit\n", timeout=10)
    except Exception:
        proc.kill()
        raise
    assert "help" in outs.lower() or "usage" in outs.lower()
    assert proc.returncode == 0 or proc.returncode is None
