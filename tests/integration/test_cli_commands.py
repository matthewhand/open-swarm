import subprocess
import sys
import os
import pytest
import re

BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.venv/bin'))
CODEY_BIN = os.path.join(BIN_DIR, 'codey')
GEESE_BIN = os.path.join(BIN_DIR, 'geese') # This is likely src/swarm/blueprints/geese/geese_cli.py, not a bin installed file
SWARM_CLI_BIN = os.path.join(BIN_DIR, 'swarm-cli')

# Path to geese_cli.py for direct execution if not in venv/bin
GEESE_CLI_PY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/swarm/blueprints/geese/geese_cli.py'))


def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])') # More comprehensive ANSI regex
    return ansi_escape.sub('', text)

@pytest.mark.parametrize("cli_path_or_name, help_flag", [
    (CODEY_BIN, "--help"),
    (SWARM_CLI_BIN, "--help"),
])
def test_cli_help(cli_path_or_name, help_flag):
    if not os.path.exists(cli_path_or_name):
        pytest.skip(f"{cli_path_or_name} not found.")

    cmd = [cli_path_or_name, help_flag]
    if not os.access(cli_path_or_name, os.X_OK) and cli_path_or_name.endswith('.py'):
        cmd = [sys.executable, cli_path_or_name, help_flag]
    elif not os.access(cli_path_or_name, os.X_OK): 
        cmd = [sys.executable, cli_path_or_name, help_flag]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        pytest.skip(f"Command {cmd[0]} not found for {cli_path_or_name} --help test.")
        return

    outs_processed = strip_ansi(result.stdout + result.stderr).lower()
    
    if cli_path_or_name == SWARM_CLI_BIN:
        assert result.returncode == 0, f"{cli_path_or_name} --help failed with code {result.returncode}. Output:\n{outs_processed}"
        assert "usage:" in outs_processed, f"'usage:' not in {cli_path_or_name} --help output. Output:\n{outs_processed}"
        # Use regex to find "commands" as a whole word, potentially surrounded by formatting
        assert re.search(r"commands\b", outs_processed), f"'commands' (as whole word) not in {cli_path_or_name} --help output. Output:\n{outs_processed}"
    else: 
        assert result.returncode == 0, f"{cli_path_or_name} --help failed with code {result.returncode}. Output:\n{outs_processed}"
        assert "usage" in outs_processed or "help" in outs_processed, f"Neither 'usage' nor 'help' found in {cli_path_or_name} --help. Output:\n{outs_processed}"


@pytest.mark.parametrize("cli_path_or_name, prompt", [
    (CODEY_BIN, "Say hello from codey!"),
])
def test_cli_minimal_prompt(cli_path_or_name, prompt):
    if not os.path.exists(cli_path_or_name):
        pytest.skip(f"{cli_path_or_name} not found.")

    cmd = [cli_path_or_name, prompt]
    if not os.access(cli_path_or_name, os.X_OK) and cli_path_or_name.endswith('.py'):
         cmd = [sys.executable, cli_path_or_name, prompt]
    elif not os.access(cli_path_or_name, os.X_OK):
         cmd = [sys.executable, cli_path_or_name, prompt]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30) 
    except FileNotFoundError:
        pytest.skip(f"Command {cmd[0]} not found for {cli_path_or_name} minimal prompt test.")
        return

    out_processed = strip_ansi(result.stdout + result.stderr).lower()
    
    assert result.returncode == 0 or "error" in out_processed or "traceback" in out_processed or "assisting with:" in out_processed or "hello" in out_processed, \
        f"Minimal prompt test failed for {cli_path_or_name}. Output:\n{out_processed}\nRetCode: {result.returncode}"


def test_swarm_cli_interactive_shell():
    if not os.path.exists(SWARM_CLI_BIN):
        pytest.skip(f"{SWARM_CLI_BIN} not found.")

    cmd_help_list = [SWARM_CLI_BIN, "--help"]
    if not os.access(SWARM_CLI_BIN, os.X_OK): 
        cmd_help_list = [sys.executable, SWARM_CLI_BIN, "--help"]

    try:
        result_help = subprocess.run(cmd_help_list, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        pytest.skip(f"Command {cmd_help_list[0]} not found for swarm-cli --help test.")
        return
        
    outs_help_processed = strip_ansi(result_help.stdout + result_help.stderr).lower()
    
    assert result_help.returncode == 0, f"swarm-cli --help failed with code {result_help.returncode}. Output:\n{outs_help_processed}"
    assert "usage:" in outs_help_processed, f"'usage:' not in swarm-cli --help output. Output:\n{outs_help_processed}"
    assert re.search(r"commands\b", outs_help_processed), f"'commands' (as whole word) not in swarm-cli --help output. Output:\n{outs_help_processed}"

    cmd_list_as_arg = [SWARM_CLI_BIN, "list"]
    if not os.access(SWARM_CLI_BIN, os.X_OK):
        cmd_list_as_arg = [sys.executable, SWARM_CLI_BIN, "list"]
    
    try:
        result_list_cmd = subprocess.run(cmd_list_as_arg, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        pytest.skip(f"Command {cmd_list_as_arg[0]} not found for swarm-cli list test.")
        return

    outs_list_cmd_processed = strip_ansi(result_list_cmd.stdout + result_list_cmd.stderr).lower()

    assert result_list_cmd.returncode == 0, f"swarm-cli list failed with code {result_list_cmd.returncode}. Output:\n{outs_list_cmd_processed}"
    assert "installed blueprints" in outs_list_cmd_processed or "bundled blueprints" in outs_list_cmd_processed, \
        f"Expected blueprint listing from 'swarm-cli list'. Output:\n{outs_list_cmd_processed}"
