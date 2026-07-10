"""Tests for swarm-cli moa-init."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_moa_init_write(tmp_path: Path):
    cfg = tmp_path / "swarm_config.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from swarm.core.swarm_cli import app; import sys; "
            "sys.argv=['swarm-cli']+sys.argv[1:]; app()",
            "moa-init",
            "--config",
            str(cfg),
            "--write",
            "--backend",
            "fake",
            "-p",
            "a,b",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["moa"]["backend"] == "fake"
    assert data["moa"]["participants"] == ["a", "b"]


def test_moa_init_show_openwebui():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from swarm.core.swarm_cli import app; import sys; "
            "sys.argv=['swarm-cli']+sys.argv[1:]; app()",
            "moa-init",
            "--show-openwebui",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["model"] == "moa"
