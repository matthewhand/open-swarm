import pytest
import subprocess
import sys
import os
import pathlib
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from swarm.core import swarm_cli

runner = CliRunner()

EXPECTED_EXE_NAME = "test_blueprint"

@pytest.fixture
def mock_dirs(tmp_path):
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

@pytest.fixture(autouse=True)
def apply_mocker_and_monkeypatch(mocker, monkeypatch): # Add monkeypatch
    # This fixture can be used to apply common patches if needed
    # For now, it just makes mocker and monkeypatch available implicitly
    pass

@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        yield mock_run


def test_swarm_cli_entrypoint():
    result = runner.invoke(swarm_cli.app, ["--help"])
    assert result.exit_code == 0
    assert "[OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "Swarm CLI tool" in result.stdout


@patch("subprocess.run") 
def test_swarm_cli_install_creates_executable(mock_pyinstaller_run, mock_dirs, mocker, monkeypatch): # Added monkeypatch
    install_bin_dir = mock_dirs["bin"]
    blueprints_src_dir = mock_dirs["blueprints"]
    user_data_dir = mock_dirs["data"]

    blueprint_name = "test_blueprint"
    target_path = install_bin_dir / blueprint_name 

    source_dir = blueprints_src_dir / blueprint_name
    source_dir.mkdir()
    entry_point_name = "main.py"
    entry_point_path = source_dir / entry_point_name
    entry_point_path.write_text("print('hello from blueprint')")

    mocker.patch("swarm.core.swarm_cli.find_entry_point", return_value=entry_point_name)
    mocker.patch.object(swarm_cli, 'BLUEPRINTS_DIR', blueprints_src_dir)
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    mocker.patch.object(swarm_cli, 'USER_DATA_DIR', user_data_dir)

    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    result_test_mode = runner.invoke(swarm_cli.app, ["install", blueprint_name])
    print(f"CLI Output (Test Mode):\n{result_test_mode.output}")
    assert result_test_mode.exit_code == 0
    assert f"Installing blueprint '{blueprint_name}'..." in result_test_mode.output
    assert f"Test-mode shim installed at: {target_path}" in result_test_mode.output 
    assert target_path.exists() 
    assert os.access(target_path, os.X_OK) 
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)

    mock_pyinstaller_process = MagicMock()
    mock_pyinstaller_process.returncode = 0
    mock_pyinstaller_process.stdout = f"PyInstaller finished successfully. Executable at {target_path}"
    mock_pyinstaller_process.stderr = ""
    mock_pyinstaller_run.return_value = mock_pyinstaller_process

    result_prod_mode = runner.invoke(swarm_cli.app, ["install", blueprint_name])
    print(f"CLI Output (Prod Mode):\n{result_prod_mode.output}")
    assert result_prod_mode.exit_code == 0
    assert f"Installing blueprint '{blueprint_name}'..." in result_prod_mode.output
    assert f"Successfully installed '{blueprint_name}' to {target_path}" in result_prod_mode.output 
    
    mock_pyinstaller_run.assert_called_once()
    args, kwargs = mock_pyinstaller_run.call_args
    cmd_list = args[0] 
    assert "pyinstaller" in cmd_list[0]
    assert str(entry_point_path) in cmd_list
    assert "--name" in cmd_list
    assert cmd_list[cmd_list.index("--name") + 1] == blueprint_name
    assert "--distpath" in cmd_list
    assert cmd_list[cmd_list.index("--distpath") + 1] == str(install_bin_dir)


@patch("subprocess.run")
def test_swarm_install_failure(mock_run, mock_dirs, mocker, monkeypatch): # Added monkeypatch
    install_bin_dir = mock_dirs["bin"]
    blueprints_src_dir = mock_dirs["blueprints"]
    user_data_dir = mock_dirs["data"]
    blueprint_name = "fail_blueprint"

    source_dir = blueprints_src_dir / blueprint_name
    source_dir.mkdir()
    entry_point_name = "fail_main.py"
    entry_point_path = source_dir / entry_point_name
    entry_point_path.write_text("print('fail')")

    mocker.patch("swarm.core.swarm_cli.find_entry_point", return_value=entry_point_name)
    error_stderr = "PyInstaller error: Build failed!"
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["pyinstaller", "..."], stderr=error_stderr
    )
    mocker.patch.object(swarm_cli, 'BLUEPRINTS_DIR', blueprints_src_dir)
    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    mocker.patch.object(swarm_cli, 'USER_DATA_DIR', user_data_dir)
    
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False) # Ensure not in test mode

    result = runner.invoke(swarm_cli.app, ["install", blueprint_name])

    assert result.exit_code == 1
    assert f"Error during PyInstaller execution" in result.output
    assert error_stderr in result.output


@patch("subprocess.run")
def test_swarm_launch_runs_executable(mock_run, mock_dirs, mocker):
    install_bin_dir = mock_dirs["bin"]
    blueprint_name = EXPECTED_EXE_NAME
    exe_path = install_bin_dir / blueprint_name

    exe_path.touch(exist_ok=True)
    exe_path.chmod(0o755)

    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Blueprint output"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    
    result = runner.invoke(
        swarm_cli.app,
        ["launch", blueprint_name], 
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"CLI failed unexpectedly. Output:\n{result.output}"
    assert f"Launching '{blueprint_name}' with: {exe_path}" in result.output 
    mock_run.assert_called_once_with([str(exe_path)], capture_output=True, text=True, check=False)


def test_swarm_launch_failure_not_found(mock_dirs, mocker):
    install_bin_dir = mock_dirs["bin"]
    blueprint_name = "nonexistent_blueprint"
    expected_path = install_bin_dir / blueprint_name

    mocker.patch.object(swarm_cli, 'INSTALLED_BIN_DIR', install_bin_dir)
    if expected_path.exists():
        expected_path.unlink()
    
    result = runner.invoke(swarm_cli.app, ["launch", blueprint_name])

    assert result.exit_code == 1
    expected_error = f"Error: Blueprint executable not found or not executable: {expected_path}"
    assert expected_error in result.output.strip()

