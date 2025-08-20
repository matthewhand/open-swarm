import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.timeout(120)
def test_packaged_codey_cli_install_and_launch(tmp_path, monkeypatch):
    """
    Integration smoke test for packaged Codey CLI:
    1) Installs codey via `swarm-cli install-executable codey`
    2) Launches the installed executable with --message under SWARM_TEST_MODE=1
    3) Asserts clean exit (rc==0) and minimally expected output contract

    Notes:
    - Skips if home bin directory is not writable
    - Skips if pyinstaller appears to be unavailable
    """
    # Prefer user home/share bin path used by swarm-cli
    user_bin = Path.home() / ".local" / "share" / "swarm" / "bin"
    codey_bin = user_bin / "codey"

    # Basic environment checks
    # PyInstaller is invoked by the CLI; do a best-effort availability check.
    pyinstaller_missing = shutil.which("pyinstaller") is None
    if pyinstaller_missing:
        # The CLI may vendor/handle PyInstaller invocation; do not hard fail on systems without it installed.
        # We allow the test to proceed and let the CLI surface a clearer error if truly required.
        pass

    # Ensure bin dir exists and is writable
    user_bin.mkdir(parents=True, exist_ok=True)
    if not os.access(user_bin, os.W_OK):
        pytest.skip(f"User bin dir not writable: {user_bin}")

    # 1) Install packaged executable
    install_cmd = ["uv", "run", "swarm-cli", "install-executable", "codey"]
    install = subprocess.run(install_cmd, capture_output=True, text=True)
    # Allow non-zero returns if already installed; still assert the binary exists
    if not codey_bin.exists():
        # Surface install logs before failing
        sys.stdout.write("\n[install stdout]\n" + install.stdout)
        sys.stderr.write("\n[install stderr]\n" + install.stderr)
        pytest.fail("codey executable was not created by install-executable")

    # 2) Launch with SWARM_TEST_MODE=1 and a benign message that should resolve quickly
    env = os.environ.copy()
    env["SWARM_TEST_MODE"] = "1"
    # Provide a simple non-search message to trigger deterministic output path
    launch_cmd = ["uv", "run", "swarm-cli", "launch", "codey", "--message", "What is a Python function?"]
    run = subprocess.run(launch_cmd, capture_output=True, text=True, env=env)

    # 3) Assertions
    if run.returncode != 0:
        sys.stdout.write("\n[launch stdout]\n" + run.stdout)
        sys.stderr.write("\n[launch stderr]\n" + run.stderr)
    assert run.returncode == 0, "Packaged codey CLI should exit cleanly (rc=0) in SWARM_TEST_MODE"

    # Minimal output contract: the test-mode branch in codey_cli prints a short knowledge answer for non-search prompts
    # e.g.: "In Python, a function is defined using the 'def' keyword."
    assert "function" in run.stdout.lower() or "def" in run.stdout.lower(), "Expected deterministic test-mode help/answer in stdout"