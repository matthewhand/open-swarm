"""XDG-first dotenv loading (unit/shell env wins, then XDG, then checkout)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from swarm.utils.dotenv_load import load_swarm_dotenv, xdg_swarm_env_path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_xdg_wins_over_project_env(tmp_path: Path):
    project = tmp_path / "project"
    xdg = tmp_path / "xdg"
    _write(project / ".env", "SHARED=from-project\nONLY_PROJECT=p\n")
    _write(xdg / "swarm" / ".env", "SHARED=from-xdg\nONLY_XDG=x\n")

    with patch.dict(
        os.environ,
        {"XDG_CONFIG_HOME": str(xdg), "PREEXISTING": "keep-me"},
        clear=True,
    ):
        loaded = load_swarm_dotenv(project_root=project)
        assert os.environ["PREEXISTING"] == "keep-me"
        assert os.environ["SHARED"] == "from-xdg"
        assert os.environ["ONLY_PROJECT"] == "p"
        assert os.environ["ONLY_XDG"] == "x"
        assert any("swarm" in item and "+2 keys" in item for item in loaded)


def test_process_env_not_overwritten_by_xdg(tmp_path: Path):
    project = tmp_path / "project"
    xdg = tmp_path / "xdg"
    _write(project / ".env", "TOKEN=from-project\n")
    _write(xdg / "swarm" / ".env", "TOKEN=from-xdg\n")

    with patch.dict(
        os.environ,
        {"XDG_CONFIG_HOME": str(xdg), "TOKEN": "from-systemd"},
        clear=True,
    ):
        load_swarm_dotenv(project_root=project)
        assert os.environ["TOKEN"] == "from-systemd"


def test_xdg_swarm_env_path_uses_xdg_config_home(tmp_path: Path):
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}, clear=False):
        assert xdg_swarm_env_path() == tmp_path / "swarm" / ".env"
