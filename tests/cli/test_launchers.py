import pytest
import subprocess
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Assuming swarm_cli.py is in src/swarm/extensions/launchers
from swarm.extensions.launchers import swarm_cli # Adjust import if needed
import PyInstaller.__main__

# Initialize runner to capture stderr separately
runner = CliRunner(mix_stderr=False)

# Fixture to ensure temp dirs exist, but remove env var patching
@pytest.fixture(autouse=True)
def test_env_dirs(tmp_path):
    # Use tmp_path provided by pytest for user directories
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    # Ensure base dirs exist, tests will patch the constants in swarm_cli
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "blueprints").mkdir(parents=True, exist_ok=True) # Ensure blueprints subdir exists
    (data_dir / "bin").mkdir(parents=True, exist_ok=True)      # Ensure bin subdir exists
    config_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Return paths for tests to use if needed (though mocker is preferred for patching)
    return {"data": data_dir, "config": config_dir, "cache": cache_dir}


def test_swarm_cli_entrypoint():
    """ Test if the CLI runs without errors (basic check). """
    result = runner.invoke(swarm_cli.app, ["--help"])
    assert result.exit_code == 0
    # Adjust assertion to match Typer runner's default prog name
    assert "Usage: root [OPTIONS] COMMAND [ARGS]..." in result.stdout

# Add 'mocker' fixture to arguments
def test_swarm_cli_install_creates_executable(tmp_path, mocker):
    """ Test 'swarm-cli install' runs PyInstaller and simulates executable creation. """
    # Paths based on tmp_path
    data_dir = tmp_path / "data"
    bp_dir = data_dir / "blueprints"
    bin_dir = data_dir / "bin"
    cache_dir = tmp_path / "cache"

    # Patch the constants within the swarm_cli module
    mocker.patch.object(swarm_cli, "BLUEPRINTS_DIR", bp_dir)
    mocker.patch.object(swarm_cli, "BIN_DIR", bin_dir) # Patch BIN_DIR too
    mocker.patch.object(swarm_cli, "BUILD_CACHE_DIR", cache_dir / "build") # Patch cache too

    # Setup dummy blueprint inside the *mocked* blueprints dir
    bp_src_dir = bp_dir / "dummy_bp"
    bp_src_dir.mkdir(parents=True, exist_ok=True)
    bp_file = bp_src_dir / "blueprint_dummy_bp.py"
    bp_file.write_text("class DummyBlueprint: pass\nprint('Hello from dummy')")

    # Mock PyInstaller run function
    mock_pyinstaller_run = MagicMock()
    final_executable_path = bin_dir / "dummy_bp" # Should be inside tmp_path now

    def simulate_pyinstaller(args):
         try:
             distpath = Path(args[args.index('--distpath') + 1])
             name = args[args.index('--name') + 1]
             distpath.mkdir(parents=True, exist_ok=True)
             (distpath / name).touch(mode=0o777)
             print(f"Simulated creating executable at: {distpath / name}")
         except Exception as e:
             print(f"Simulate pyinstaller file creation failed (continuing): {e}")
             pass
         mock_pyinstaller_run(args)

    with patch.object(PyInstaller.__main__, "run", side_effect=simulate_pyinstaller) as patched_run:
         # Note: We don't need --bin-dir override anymore if we patch swarm_cli.BIN_DIR
         result = runner.invoke(
             swarm_cli.app,
             ["install", "dummy_bp"], # No --bin-dir needed
             catch_exceptions=False
         )

    # Assertions
    assert result.exit_code == 0, f"CLI failed unexpectedly. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    patched_run.assert_called_once()
    mock_pyinstaller_run.assert_called_once()
    assert final_executable_path.exists(), f"Executable file was not created at {final_executable_path}"
    assert os.access(final_executable_path, os.X_OK), "Executable file doesn't have execute permissions"

# Add 'mocker' fixture
def test_swarm_install_failure(tmp_path, mocker):
    """Test install command fails and exits if blueprint doesn't exist."""
    # Patch BLUEPRINTS_DIR to use tmp_path
    bp_dir = tmp_path / "data" / "blueprints"
    mocker.patch.object(swarm_cli, "BLUEPRINTS_DIR", bp_dir)

    # Don't create the blueprint file/dir within the mocked bp_dir
    result = runner.invoke(swarm_cli.app, ["install", "nonexistent_blueprint"])
    assert result.exit_code != 0
    assert "Error: Blueprint directory or entrypoint file not found" in result.stderr
    # Check that the error message uses the patched path
    assert str(bp_dir) in result.stderr

# Add 'mocker' fixture
def test_swarm_launch_runs_executable(tmp_path, mocker):
    """ Test 'swarm-cli launch' executes the correct pre-installed executable. """
    # Paths based on tmp_path
    data_dir = tmp_path / "data"
    bin_dir = data_dir / "bin"

    # Patch BIN_DIR constant in swarm_cli
    mocker.patch.object(swarm_cli, "BIN_DIR", bin_dir)

    # Setup dummy executable in the *mocked* bin dir
    exe_path = bin_dir / "test_bp"
    # Ensure bin_dir exists
    bin_dir.mkdir(parents=True, exist_ok=True)
    # FIX: Use "$*" within the echo string to correctly print all arguments
    exe_path.write_text(f"#!/bin/sh\necho \"Test BP Launched with args: $*\"\necho 'Output to file' > {tmp_path}/output.txt")
    os.chmod(exe_path, 0o777)

    # Invoke the launch command
    result = runner.invoke(
        swarm_cli.app,
        ["launch", "test_bp", "--", "arg1", "--option=val"],
        catch_exceptions=False
    )

    # Assertions
    assert result.exit_code == 0, f"CLI failed unexpectedly. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # Check stdout from the launched process (captured by runner)
    assert "Test BP Launched with args: arg1 --option=val" in result.stdout
    # Check side effect file
    output_file = tmp_path / "output.txt"
    assert output_file.exists(), "Executable did not create side effect file"
    output_file.unlink()

