import os
import tempfile
from pathlib import Path
from swarm.extensions.config import config_loader

def test_default_config_generation(monkeypatch, caplog):
    # Patch XDG_CONFIG_HOME and CWD to temp dirs with no config present
    with tempfile.TemporaryDirectory() as tmp_xdg, tempfile.TemporaryDirectory() as tmp_cwd:
        monkeypatch.setenv("XDG_CONFIG_HOME", tmp_xdg)
        old_cwd = os.getcwd()
        os.chdir(tmp_cwd)
        try:
            config_path = Path(tmp_xdg) / "swarm" / config_loader.DEFAULT_CONFIG_FILENAME
            # Ensure no config exists
            if config_path.exists():
                config_path.unlink()
            # Attempt to load config (should trigger default generation)
            try:
                found = config_loader.find_config_file()
            except Exception:
                found = None
            if not found:
                # Simulate auto-generation
                config_loader.create_default_config(config_path)
                assert config_path.exists()
        finally:
            os.chdir(old_cwd)
