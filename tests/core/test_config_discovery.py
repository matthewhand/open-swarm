import os
import tempfile
from pathlib import Path

from swarm.core import config_loader


def test_xdg_config_discovery(monkeypatch):
    # Create a temp XDG config file
    with tempfile.TemporaryDirectory() as tmpdir:
        xdg_config_dir = Path(tmpdir) / "swarm"
        xdg_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = xdg_config_dir / config_loader.DEFAULT_CONFIG_FILENAME
        config_path.write_text('{"llm": {"qwen3.5": {"provider": "openai", "model": "qwen3.5"}}}')
        monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
        found = config_loader.find_config_file()
        assert found is not None
        assert found.samefile(config_path)

def test_config_fallback_to_cwd(monkeypatch):
    # Patch XDG_CONFIG_HOME to a temp dir with NO config file present
    with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as fake_xdg:
        monkeypatch.setenv("XDG_CONFIG_HOME", fake_xdg)
        cwd = Path(tmpdir)
        config_path = cwd / config_loader.DEFAULT_CONFIG_FILENAME
        config_path.write_text('{"llm": {"qwen3.5": {"provider": "openai", "model": "qwen3.5"}}}')
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            found = config_loader.find_config_file()
            assert found is not None
            assert found.samefile(config_path)
        finally:
            os.chdir(old_cwd)
