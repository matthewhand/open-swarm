
# --- Content for tests/cli/test_launchers.py ---
import pytest
import subprocess
import sys
import os
import pathlib
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Corrected import path
from swarm.extensions.launchers import swarm_cli

runner = CliRunner()

EXPECTED_EXE_NAME = "test_blueprint"

@pytest.fixture
def mock_dirs(tmp_path):
    """Creates temporary directories and returns their paths."""
    mock_user_data_dir = tmp_path / "user_data"
    mock_user_bin_dir = mock_user_data_dir / "bin"
    mock_user_blueprints_dir = mock_user_data_dir / "blueprints"

    mock_user_bin_dir.mkdir(parents=True, exist_ok=True)
    mock_user_blueprints_dir.mkdir(parents=True, exist_ok=True)

    return {
        "data": mock_user_data_dir,
        "bin": mock_user_bin_dir,
        "blueprints": mock_user_blueprints_dir,
    }

# This fixture is needed because mock_dirs uses mocker
@pytest.fixture(autouse=True)
def apply_mocker(mocker):
    pass

@pytest.fixture
def mock_subprocess_run():
    """Mocks subprocess.run."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        yield mock_run


def test_swarm_cli_entrypoint():
    """Test that the CLI runs and shows help."""
    result = runner.invoke(swarm_cli.app, ["--help"])
    assert result.exit_code == 0
    assert "[OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "Swarm CLI tool" in result.stdout


@patch("subprocess.run")
def test_swarm_cli_install_creates_executable(mock_run, mock_dirs, mocker):
    """Test the install command attempts to run PyInstaller."""
    install_bin_dir = mock_dirs["bin"]
    blueprints_src_dir = mock_dirs["blueprints"]
    user_data_dir = mock_dirs["data"]

    blueprint_name = "test_blueprint"
    target_path = install_bin_dir / blueprint_name

    # Simulate Source Blueprint Directory and File
    source_dir = blueprints_src_dir / blueprint_name
    source_dir.mkdir()
    entry_point_name = "main.py"
    entry_point_path = source_dir / entry_point_name
    entry_point_path.write_text("print('hello from blueprint')")

    # Mock find_entry_point
    mocker.patch("swarm.extensions.launchers.swarm_cli.find_entry_point", return_value=entry_point_name)

    # Configure mock for successful PyInstaller run
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = f"PyInstaller finished successfully. Executable at {target_path}"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    # --- Patch Module-Level Variables Directly ---
    mocker.patch.object(swarm_cli, 'BLUEPRINTS_DIR', blueprints_src_dir)
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    mocker.patch.object(swarm_cli, 'USER_DATA_DIR', user_data_dir)

    result = runner.invoke(swarm_cli.app, ["install", blueprint_name])

    print(f"CLI Output:\n{result.output}")
    print(f"CLI Exit Code: {result.exit_code}")
    print(f"CLI Exception: {result.exception}")

    assert result.exit_code == 0, f"CLI failed unexpectedly. Output:\n{result.output}"
    assert f"Installing blueprint '{blueprint_name}'..." in result.output
    assert f"Successfully installed '{blueprint_name}' to {target_path}" in result.output

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    cmd_list = args[0] # Get the command list
    assert "pyinstaller" in cmd_list[0]
    assert str(entry_point_path) in cmd_list
    # --- Corrected --name assertion ---
    assert "--name" in cmd_list
    assert cmd_list[cmd_list.index("--name") + 1] == blueprint_name
    # --- End correction ---
    assert "--distpath" in cmd_list
    assert cmd_list[cmd_list.index("--distpath") + 1] == str(install_bin_dir)
    assert "--workpath" in cmd_list
    assert cmd_list[cmd_list.index("--workpath") + 1] == str(user_data_dir / "build") # Check specific build path
    assert "--specpath" in cmd_list
    assert cmd_list[cmd_list.index("--specpath") + 1] == str(user_data_dir)


@patch("subprocess.run")
def test_swarm_install_failure(mock_run, mock_dirs, mocker):
    """Test the install command handles PyInstaller failure."""
    install_bin_dir = mock_dirs["bin"]
    blueprints_src_dir = mock_dirs["blueprints"]
    user_data_dir = mock_dirs["data"]
    blueprint_name = "fail_blueprint"

    # Simulate Source Blueprint Directory and File
    source_dir = blueprints_src_dir / blueprint_name
    source_dir.mkdir()
    entry_point_name = "fail_main.py"
    entry_point_path = source_dir / entry_point_name
    entry_point_path.write_text("print('fail')")

    # Mock find_entry_point
    mocker.patch("swarm.extensions.launchers.swarm_cli.find_entry_point", return_value=entry_point_name)

    # --- Configure mock to RAISE CalledProcessError ---
    error_stderr = "PyInstaller error: Build failed!"
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["pyinstaller", "..."], stderr=error_stderr
    )
    # --- End change ---

    # --- Patch Module-Level Variables Directly ---
    mocker.patch.object(swarm_cli, 'BLUEPRINTS_DIR', blueprints_src_dir)
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    mocker.patch.object(swarm_cli, 'USER_DATA_DIR', user_data_dir)

    result = runner.invoke(swarm_cli.app, ["install", blueprint_name])

    assert result.exit_code == 1
    assert f"Error during PyInstaller execution" in result.output
    assert error_stderr in result.output


@patch("subprocess.run")
def test_swarm_launch_runs_executable(mock_run, mock_dirs, mocker):
    """Test the launch command runs the correct executable."""
    install_bin_dir = mock_dirs["bin"]
    blueprint_name = EXPECTED_EXE_NAME
    exe_path = install_bin_dir / blueprint_name

    # Simulate the executable existing in the mocked bin dir
    exe_path.touch(exist_ok=True)
    exe_path.chmod(0o755)

    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Blueprint output"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    # --- Patch Module-Level INSTALLED_BIN_DIR ---
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    # Patch file checks used by launch command
    mocker.patch('pathlib.Path.is_file', return_value=True)
    mocker.patch('os.access', return_value=True)

    result = runner.invoke(
        swarm_cli.app,
        ["launch", blueprint_name], # No extra args
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"CLI failed unexpectedly. Output:\n{result.output}"
    assert f"Launching '{blueprint_name}' from {exe_path}..." in result.output
    mock_run.assert_called_once_with([str(exe_path)], capture_output=True, text=True, check=False)


def test_swarm_launch_failure_not_found(mock_dirs, mocker):
    """Test the launch command fails if the executable doesn't exist."""
    install_bin_dir = mock_dirs["bin"]
    blueprint_name = "nonexistent_blueprint"
    expected_path = install_bin_dir / blueprint_name

    # --- Patch Module-Level INSTALLED_BIN_DIR ---
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    # Patch file checks to return False
    mocker.patch('pathlib.Path.is_file', return_value=False)
    mocker.patch('os.access', return_value=False)

    result = runner.invoke(swarm_cli.app, ["launch", blueprint_name])

    assert result.exit_code == 1
    expected_error = f"Error: Blueprint executable not found or not executable: {expected_path}"
    assert expected_error in result.output.strip()

