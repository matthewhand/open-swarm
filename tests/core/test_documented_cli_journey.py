import subprocess
import os
import tempfile
from pathlib import Path

def test_documented_cli_journey():
    """Integration test for documented CLI journey per strategy."""
    env = os.environ.copy()
    env["SWARM_TEST_MODE"] = "1"
    # list
    res = subprocess.run(["swarm-cli", "list", "--available"], env=env, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0
    assert "codey" in res.stdout or "suggestion" in res.stdout
    # install
    res = subprocess.run(["swarm-cli", "install-executable", "codey"], env=env, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0
    assert "Entry Point: codey_cli.py" in res.stdout
    # launch with --message (documented path); in test mode produces real spinner/box output
    res = subprocess.run(["swarm-cli", "launch", "codey", "--message", "journey test"], env=env, capture_output=True, text=True, timeout=30)
    out = res.stdout + res.stderr
    assert "codey" in out.lower() or "Code Search" in out or "SPINNER" in out
    assert "Entry Point" not in out  # not in launch
    assert "nameerror" not in out.lower() and "attributeerror" not in out.lower() and "unbound" not in out.lower()
    # list shows the priority entry
    res = subprocess.run(["swarm-cli", "list"], env=env, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0
    assert "codey (entry: codey_cli.py)" in res.stdout or "codey_cli.py" in res.stdout
