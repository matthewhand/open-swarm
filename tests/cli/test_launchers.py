import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import os

# Import swarm_cli at the module level
from swarm.extensions.launchers import swarm_cli

# Use the paths defined in swarm_cli for consistency
# These will be patched by the fixture
MANAGED_DIR_ORIG = swarm_cli.MANAGED_DIR
BIN_DIR_ORIG = swarm_cli.BIN_DIR
DEFAULT_CONFIG_PATH_ORIG = swarm_cli.DEFAULT_CONFIG_PATH


@pytest.fixture(autouse=True)
def manage_swarm_dirs(tmp_path, monkeypatch): # Added monkeypatch here
    """ Ensures swarm directories exist for tests and are cleaned up. """
    managed_dir = tmp_path / "managed_blueprints"
    bin_dir = tmp_path / "bin"
    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    data_dir = tmp_path / "data" # Define data dir if needed by ensure_swarm_dirs

    paths_to_patch = {
        'MANAGED_DIR': managed_dir,
        'BIN_DIR': bin_dir,
        'DEFAULT_CONFIG_PATH': config_dir / 'swarm_config.json',
        'BUILD_CACHE_DIR': cache_dir / 'build',
        'SWARM_CONFIG_DIR': config_dir,
        'SWARM_DATA_DIR': data_dir, # Patch this as well
        'SWARM_CACHE_DIR': cache_dir,
    }

    # Apply patches using monkeypatch fixture for better control
    for name, path_obj in paths_to_patch.items():
         monkeypatch.setattr(swarm_cli, name, path_obj, raising=False)

    # Ensure patched dirs exist before test
    for path_obj in paths_to_patch.values():
         if str(path_obj).endswith('.json'): # Only create parent for file paths
              path_obj.parent.mkdir(parents=True, exist_ok=True)
         else:
              path_obj.mkdir(parents=True, exist_ok=True)

    yield # Run the test
    # tmp_path fixture handles cleanup


def test_swarm_cli_install_creates_executable(monkeypatch, tmp_path, capsys):
    """ Test that 'swarm-cli install' runs PyInstaller and simulates executable creation. """
    bp_src_dir = tmp_path / "bp_source"; bp_src_dir.mkdir()
    blueprint_file = bp_src_dir / "blueprint_dummy_blueprint.py"
    blueprint_file.write_text("""
import sys
# Need to ensure imports work relative to where PyInstaller runs from
# Assuming swarm package is in PYTHONPATH or site-packages
try: from swarm.extensions.blueprint import BlueprintBase
except ImportError: sys.path.insert(0, '/path/to/your/project/src'); from swarm.extensions.blueprint import BlueprintBase # Adjust path
try: from agents import Agent
except ImportError: sys.path.insert(0, '/path/to/your/project/src'); from agents import Agent # Adjust path

class DummyAgent(Agent):
    async def process(self, messages, **kwargs): return "Dummy Done"
class DummyBlueprint(BlueprintBase):
    metadata = {"name": "DummyBlueprint"}
    def create_starting_agent(self, mcp_servers): return DummyAgent()
if __name__ == "__main__": DummyBlueprint.main()
""")

    # Mock PyInstaller to avoid actual build time AND simulate file creation
    mock_pyinstaller_run = MagicMock()
    final_executable_path = swarm_cli.BIN_DIR / "dummy_blueprint"
    def simulate_pyinstaller(*args, **kwargs):
         final_executable_path.touch(mode=0o666)
         mock_pyinstaller_run(*args, **kwargs)
    monkeypatch.setattr(swarm_cli.PyInstaller.__main__, "run", simulate_pyinstaller)

    mock_chmod = MagicMock(); monkeypatch.setattr(Path, "chmod", mock_chmod)

    # 1. Add blueprint
    add_args = ["swarm-cli", "add", str(bp_src_dir), "--name", "dummy_blueprint"]
    monkeypatch.setattr(sys, "argv", add_args); swarm_cli.main()
    managed_bp_file = swarm_cli.MANAGED_DIR / "dummy_blueprint" / "blueprint_dummy_blueprint.py"
    assert managed_bp_file.exists()

    # 2. Install blueprint
    install_args = ["swarm-cli", "install", "dummy_blueprint"]
    monkeypatch.setattr(sys, "argv", install_args); swarm_cli.main()

    # Assertions
    assert mock_pyinstaller_run.called
    mock_chmod.assert_called_once()
    assert mock_chmod.call_args[0][0] & 0o111 != 0
    captured = capsys.readouterr().out
    assert f"Success! Installed 'dummy_blueprint' to {final_executable_path}" in captured, captured

def test_swarm_install_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["swarm-cli", "install", "nonexistent"])
    with pytest.raises(SystemExit): swarm_cli.main()

def test_swarm_cli_creates_default_config(monkeypatch, tmp_path):
    """ Test 'swarm-cli run' creates default config if missing. """
    config_path = swarm_cli.DEFAULT_CONFIG_PATH
    if config_path.exists(): config_path.unlink()
    assert not config_path.exists() # Verify deletion

    mock_run_bp = MagicMock()
    monkeypatch.setattr(swarm_cli, "run_blueprint", mock_run_bp)

    test_args = ["swarm-cli", "run", "dummy_bp"]
    monkeypatch.setattr(sys, "argv", test_args)
    swarm_cli.main()

    assert config_path.exists(), f"Config file should exist at {config_path}"
    mock_run_bp.assert_called_once_with("dummy_bp", [], config_path_override=None) # Check args passed to mock
    with open(config_path, 'r') as f: content = json.load(f)
    assert "llm" in content and "mcpServers" in content

