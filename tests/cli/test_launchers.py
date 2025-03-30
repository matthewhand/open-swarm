import pytest
import subprocess
from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY # Import ANY

# Assuming swarm_cli.py is now at src/swarm/extensions/launchers/swarm_cli.py
# Adjust the import path if necessary
try:
    from swarm.extensions.launchers import swarm_cli
except ImportError:
    # Fallback or handle error if structure is different
    pytest.fail("Could not import swarm_cli module. Check path.")

# *** Initialize runner to NOT mix stderr ***
runner = CliRunner(mix_stderr=False)

# --- Fixtures ---

@pytest.fixture(autouse=True)
def isolate_filesystem(monkeypatch, tmp_path):
    """Ensure tests don't interact with the real user filesystem."""
    # Use tmp_path provided by pytest for isolation
    mock_user_data_dir = tmp_path / "swarm_user_data"
    mock_user_config_dir = tmp_path / "swarm_user_config"
    # Define the bin dir within the mocked data dir
    mock_user_bin_dir = mock_user_data_dir / "bin"

    # Ensure mocked dirs exist for the test
    mock_user_data_dir.mkdir(parents=True, exist_ok=True)
    mock_user_config_dir.mkdir(parents=True, exist_ok=True)
    mock_user_bin_dir.mkdir(parents=True, exist_ok=True) # Ensure bin dir exists

    # Patch platformdirs functions used in swarm_cli
    monkeypatch.setattr(swarm_cli.platformdirs, "user_data_dir", lambda *args, **kwargs: str(mock_user_data_dir))
    monkeypatch.setattr(swarm_cli.platformdirs, "user_config_dir", lambda *args, **kwargs: str(mock_user_config_dir))
    # Patch the derived directory variables directly in the module where they are defined
    monkeypatch.setattr(swarm_cli, "USER_DATA_DIR", mock_user_data_dir)
    monkeypatch.setattr(swarm_cli, "USER_CONFIG_DIR", mock_user_config_dir)
    monkeypatch.setattr(swarm_cli, "USER_BIN_DIR", mock_user_bin_dir)
    monkeypatch.setattr(swarm_cli, "BLUEPRINTS_DIR", mock_user_data_dir / "blueprints")
    monkeypatch.setattr(swarm_cli, "INSTALLED_BIN_DIR", mock_user_bin_dir) # Patch the correct variable


# --- Tests ---

def test_swarm_cli_entrypoint():
    """Test that the CLI runs and shows help."""
    result = runner.invoke(swarm_cli.app, ["--help"])
    assert result.exit_code == 0
    # *** Adjust assertion to expect 'root' in test runner context ***
    assert "Usage: root [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "install" in result.stdout
    assert "launch" in result.stdout
    assert "list" in result.stdout


# Mock subprocess.run used by the install command
@patch('subprocess.run')
def test_swarm_cli_install_creates_executable(mock_subprocess_run, tmp_path, monkeypatch):
    """ Test 'swarm-cli install' runs PyInstaller and simulates executable creation. """
    # Use paths derived from the isolated filesystem fixture
    mock_user_data_dir = swarm_cli.USER_DATA_DIR
    mock_bp_dir = swarm_cli.BLUEPRINTS_DIR
    mock_bin_dir = swarm_cli.INSTALLED_BIN_DIR # Use the correct variable

    # Ensure mocked dirs exist (should be handled by fixture, but double-check)
    mock_bp_dir.mkdir(parents=True, exist_ok=True)
    mock_bin_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy blueprint source directory and entry point file
    blueprint_name = "dummy_install_bp"
    source_bp_path = mock_bp_dir / blueprint_name
    source_bp_path.mkdir()
    entry_point_name = "main.py"
    (source_bp_path / entry_point_name).touch()

    # Configure the mock for subprocess.run
    # Simulate successful PyInstaller run (no output needed, just check call)
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout="PyInstaller success", stderr=""
    )

    # Invoke the install command
    result = runner.invoke(swarm_cli.app, ["install", blueprint_name])

    # Assertions
    assert result.exit_code == 0, f"CLI exited with code {result.exit_code}. Output:\n{result.stdout}\n{result.stderr}"
    assert f"Installing blueprint '{blueprint_name}'..." in result.stdout
    assert f"Successfully installed '{blueprint_name}'" in result.stdout

    # Check that subprocess.run (PyInstaller) was called correctly
    expected_pyinstaller_cmd_start = [
        "pyinstaller",
        "--onefile",
        "--name", blueprint_name,
        "--distpath", str(mock_bin_dir), # Check correct output path
        # Check other paths point within tmp_path structure
        "--workpath", str(mock_user_data_dir / "build"),
        "--specpath", str(mock_user_data_dir),
        str(source_bp_path / entry_point_name),
    ]
    mock_subprocess_run.assert_called_once()
    called_args = mock_subprocess_run.call_args[0][0] # Get the list passed to subprocess.run
    assert called_args == expected_pyinstaller_cmd_start


@patch('subprocess.run') # Mock subprocess even if not expected to be called
def test_swarm_install_failure(mock_subprocess_run, tmp_path, monkeypatch):
    """Test install command fails and exits if blueprint doesn't exist."""
    # Use paths derived from the isolated filesystem fixture
    mock_bp_dir = swarm_cli.BLUEPRINTS_DIR
    mock_bp_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    # Don't create the blueprint source dir
    blueprint_name = "nonexistent_blueprint"
    result = runner.invoke(swarm_cli.app, ["install", blueprint_name])

    # Assertions
    assert result.exit_code != 0
    # Check stderr for the error message (should work now with mix_stderr=False)
    expected_error = f"Error: Blueprint source directory not found in user directory: {mock_bp_dir / blueprint_name}"
    assert expected_error in result.stderr
    assert "Currently, only blueprints placed in the user directory can be installed." in result.stderr
    mock_subprocess_run.assert_not_called() # PyInstaller should not have been called


@patch('subprocess.run')
def test_swarm_launch_runs_executable(mock_subprocess_run, tmp_path, monkeypatch):
    """ Test 'swarm-cli launch' executes the correct pre-installed executable. """
    # Use paths derived from the isolated filesystem fixture
    mock_bin_dir = swarm_cli.INSTALLED_BIN_DIR # Use the correct variable
    mock_bin_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    # Create a dummy executable file in the mocked bin directory
    blueprint_name = "dummy_launch_bp"
    executable_path = mock_bin_dir / blueprint_name
    executable_path.touch()
    executable_path.chmod(0o755) # Make it executable

    # Configure the mock for subprocess.run (simulating the launched blueprint)
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout=f"Launched {blueprint_name} successfully!", stderr=""
    )

    # Invoke the launch command
    result = runner.invoke(swarm_cli.app, ["launch", blueprint_name])

    # Assertions
    assert result.exit_code == 0, f"CLI exited with code {result.exit_code}. Output:\n{result.stdout}\n{result.stderr}"
    assert f"Launching '{blueprint_name}' from {executable_path}..." in result.stdout
    assert f"Launched {blueprint_name} successfully!" in result.stdout # Check blueprint output

    # Check that subprocess.run was called to execute the blueprint
    mock_subprocess_run.assert_called_once_with(
        [str(executable_path)], capture_output=True, text=True, check=False
    )


def test_swarm_launch_failure_not_found(tmp_path, monkeypatch):
    """Test launch command fails if executable doesn't exist."""
    # Use paths derived from the isolated filesystem fixture
    mock_bin_dir = swarm_cli.INSTALLED_BIN_DIR # Use the correct variable
    mock_bin_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    blueprint_name = "nonexistent_launch_bp"
    result = runner.invoke(swarm_cli.app, ["launch", blueprint_name])

    # Assertions
    assert result.exit_code != 0
    expected_error = f"Error: Blueprint executable not found or not executable: {mock_bin_dir / blueprint_name}"
    # Check stderr for the error message (should work now with mix_stderr=False)
    assert expected_error in result.stderr

