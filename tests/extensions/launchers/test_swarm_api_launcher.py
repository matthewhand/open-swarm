
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock, call, mock_open
import os

# Assume the script is importable relative to the project structure
# Adjust the import path if your test runner setup requires it
from swarm.extensions.launchers.swarm_api import main as swarm_api_main

# --- Test Cases ---

@patch('swarm.extensions.launchers.swarm_api.subprocess.run')
@patch('swarm.extensions.launchers.swarm_api.path.exists')
@patch('swarm.extensions.launchers.swarm_api.path.isdir')
@patch('swarm.extensions.launchers.swarm_api.listdir')
@patch('swarm.extensions.launchers.swarm_api.path.expanduser')
@patch('swarm.extensions.launchers.swarm_api.makedirs')
@patch('builtins.open', new_callable=mock_open) # Mock open for config file
def test_swarm_api_basic_run(
    mock_file_open, mock_makedirs, mock_expanduser, mock_listdir,
    mock_isdir, mock_exists, mock_subprocess_run
):
    """Test basic execution with a managed blueprint name."""
    # --- Mock Setup ---
    # Simulate command line arguments
    test_args = ['swarm-api', '--blueprint', 'echocraft']
    with patch.object(sys, 'argv', test_args):
        # Mock expanduser to return predictable paths
        mock_expanduser.side_effect = lambda p: p.replace("~", "/fake/home")

        # Mock filesystem checks for finding the managed blueprint
        managed_bp_dir = "/fake/home/.swarm/blueprints/echocraft"
        managed_bp_file = os.path.join(managed_bp_dir, "blueprint_echocraft.py")

        mock_exists.side_effect = lambda p: p == managed_bp_file or p == "/fake/home/.swarm/swarm_config.json"
        mock_isdir.side_effect = lambda p: p == managed_bp_dir # Dir exists
        mock_listdir.return_value = ['blueprint_echocraft.py', 'other_file.txt'] # Found blueprint file

        # --- Execute ---
        swarm_api_main()

        # --- Assertions ---
        # Check if runserver was called with default port
        default_port = 8000
        expected_call = call(['python', 'manage.py', 'runserver', f'0.0.0.0:{default_port}'], check=True)
        mock_subprocess_run.assert_has_calls([expected_call])
        # Check config file wasn't created (mock_exists returned True)
        mock_makedirs.assert_not_called()
        mock_file_open.assert_not_called()


@patch('swarm.extensions.launchers.swarm_api.subprocess.run')
@patch('swarm.extensions.launchers.swarm_api.path.exists')
@patch('swarm.extensions.launchers.swarm_api.path.expanduser')
@patch('swarm.extensions.launchers.swarm_api.makedirs')
@patch('builtins.open', new_callable=mock_open) # Mock open for config file
def test_swarm_api_custom_port_and_config_creation(
    mock_file_open, mock_makedirs, mock_expanduser, mock_exists, mock_subprocess_run
):
    """Test custom port and config file creation."""
    # --- Mock Setup ---
    test_args = ['swarm-api', '--blueprint', '/path/to/my_bp.py', '--port', '9999', '--config', '/tmp/my_swarm.json']
    with patch.object(sys, 'argv', test_args):
        mock_expanduser.side_effect = lambda p: p # No ~ expansion needed here
        # Simulate blueprint file exists, but config file does NOT
        mock_exists.side_effect = lambda p: p == '/path/to/my_bp.py'

        # --- Execute ---
        swarm_api_main()

        # --- Assertions ---
        # Check runserver called with custom port
        custom_port = 9999
        expected_run_call = call(['python', 'manage.py', 'runserver', f'0.0.0.0:{custom_port}'], check=True)
        mock_subprocess_run.assert_has_calls([expected_run_call])

        # Check config directory and file were created
        mock_makedirs.assert_called_once_with('/tmp', exist_ok=True)
        mock_file_open.assert_called_once_with('/tmp/my_swarm.json', 'w')
        mock_file_open().write.assert_called_once_with("{}")


@patch('swarm.extensions.launchers.swarm_api.subprocess.Popen')
@patch('swarm.extensions.launchers.swarm_api.path.exists')
@patch('swarm.extensions.launchers.swarm_api.path.expanduser')
def test_swarm_api_daemon_mode(mock_expanduser, mock_exists, mock_subprocess_popen):
    """Test daemon mode uses Popen."""
    # --- Mock Setup ---
    test_args = ['swarm-api', '--blueprint', '/bp/direct.py', '--daemon']
    # Mock Popen to return a fake process object with a pid
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_subprocess_popen.return_value = mock_proc

    with patch.object(sys, 'argv', test_args):
        mock_expanduser.side_effect = lambda p: p
        mock_exists.return_value = True # Assume blueprint and config exist

        # --- Execute ---
        swarm_api_main()

        # --- Assertions ---
        # Check Popen was called instead of run
        default_port = 8000
        expected_popen_call = call(['python', 'manage.py', 'runserver', f'0.0.0.0:{default_port}'])
        mock_subprocess_popen.assert_has_calls([expected_popen_call])


@patch('swarm.extensions.launchers.swarm_api.subprocess.run')
@patch('swarm.extensions.launchers.swarm_api.path.exists')
@patch('swarm.extensions.launchers.swarm_api.path.expanduser')
def test_swarm_api_blueprint_not_found(mock_expanduser, mock_exists, mock_subprocess_run):
    """Test script exits if blueprint is not found."""
    # --- Mock Setup ---
    test_args = ['swarm-api', '--blueprint', 'nonexistent_bp']
    with patch.object(sys, 'argv', test_args):
        mock_expanduser.side_effect = lambda p: p.replace("~", "/fake/home")
        mock_exists.return_value = False # Blueprint and config don't exist

        # --- Execute & Assert ---
        # Check that the script calls sys.exit (implicitly or explicitly)
        with pytest.raises(SystemExit) as excinfo:
            swarm_api_main()
        # Optionally check the exit code if your script sets it
        assert excinfo.value.code == 1

        # Ensure runserver was NOT called
        mock_subprocess_run.assert_not_called()

