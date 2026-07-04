import subprocess
import os
import tempfile
from pathlib import Path

def _run_cli(args, env=None, timeout=30):
    """Drive the shipped primary entrypoint via python -m so expanded commands are tested."""
    if env is None:
        env = os.environ.copy()
    env["SWARM_TEST_MODE"] = "1"
    cmd = ["python3", "-m", "swarm.core.swarm_cli"] + args
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)

def test_documented_cli_journey():
    """Integration test for documented CLI journey per strategy.
    Now drives the expanded config/wizard/lifecycle sections as well.
    """
    # list
    res = _run_cli(["list", "--available"])
    assert res.returncode == 0
    assert "codey" in res.stdout or "suggestion" in res.stdout
    # install
    res = _run_cli(["install-executable", "codey"])
    assert res.returncode == 0
    assert "Entry Point: codey_cli.py" in res.stdout
    # launch with --message (documented path)
    res = _run_cli(["launch", "codey", "--message", "journey test"])
    out = res.stdout + res.stderr
    assert "codey" in out.lower() or "Code Search" in out or "SPINNER" in out
    assert "Entry Point" not in out
    assert "nameerror" not in out.lower() and "attributeerror" not in out.lower() and "unbound" not in out.lower()
    # list shows the priority entry
    res = _run_cli(["list"])
    assert res.returncode == 0
    assert "codey (entry: codey_cli.py)" in res.stdout or "codey_cli.py" in res.stdout

    # Expanded coverage: config (real add + list, verify side effect)
    res = _run_cli(["config", "add", "--section", "llm", "--name", "journey_prof", "--json", '{"provider":"openai","model":"gpt-4o-mini","base_url":"https://api.openai.com/v1","api_key":"${OPENAI_API_KEY}"}'])
    assert res.returncode == 0
    assert "Added" in res.stdout
    res = _run_cli(["config", "list", "--section", "llm"])
    assert res.returncode == 0
    assert "journey_prof" in res.stdout

    # Expanded: wizard non-interactive (documented in guide) - verify file created
    import shutil, os
    wiz_dir = "/tmp/journey-wiz"
    # force clean to avoid "already exists" from prior partial runs or test pollution
    if os.path.exists(wiz_dir):
        shutil.rmtree(wiz_dir)
    os.makedirs(wiz_dir, exist_ok=True)  # ensure parent
    res = _run_cli(["wizard", "--non-interactive", "-n", "JourneyTeam", "-r", "Lead:coord", "--no-shortcut", "--output-dir", wiz_dir])
    assert res.returncode == 0
    assert "Team blueprint created" in res.stdout
    assert os.path.exists(f"{wiz_dir}/journeyteam/blueprint_journeyteam.py")

    # Expanded: add / delete / uninstall lifecycle - verify side effects
    add_src = f"{wiz_dir}/journeyteam"
    res = _run_cli(["add", add_src, "--name", "journeyteam"])
    assert res.returncode == 0
    user_bp = os.path.expanduser("~/.local/share/swarm/blueprints/journeyteam")
    assert os.path.exists(user_bp)
    res = _run_cli(["delete", "journeyteam"])
    assert res.returncode == 0
    assert not os.path.exists(user_bp)

    # complete lifecycle: install-executable then uninstall, assert gone
    # use a source that has entry point, e.g. the wiz one or codey
    res = _run_cli(["install-executable", "codey"])  # or journey one if exists
    assert res.returncode == 0
    user_bin = os.path.expanduser("~/.local/share/swarm/bin/codey")
    assert os.path.exists(user_bin)
    res = _run_cli(["uninstall", "codey"])
    assert res.returncode == 0
    assert not os.path.exists(user_bin)

