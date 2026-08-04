import shutil
from pathlib import Path

from tests.xdg_isolation import pin_xdg_env, run_swarm_cli


def _run_cli(args, env, timeout=30):
    """Drive the shipped primary entrypoint via python -m so expanded commands are tested.

    ``env`` must already be XDG-isolated (see ``pin_xdg_env``); pins are reused.
    """
    return run_swarm_cli(
        *args,
        env=env,
        module="swarm.core.swarm_cli",
        timeout=timeout,
    )


def test_documented_cli_journey(tmp_path: Path):
    """Integration test for documented CLI journey per strategy.
    Now drives the expanded config/wizard/lifecycle sections as well.
    """
    # Traditional home layout so expanduser("~/.local/share/swarm/...") matches
    # SWARM_USER_DATA_DIR under the isolated home.
    home = tmp_path / "home"
    env = pin_xdg_env(home=home, overrides={"SWARM_TEST_MODE": "1"})
    data_root = Path(env["SWARM_USER_DATA_DIR"])

    # list
    res = _run_cli(["list", "--available"], env)
    assert res.returncode == 0
    assert "codey" in res.stdout or "suggestion" in res.stdout
    # install
    res = _run_cli(["install-executable", "codey"], env)
    assert res.returncode == 0, res.stderr + res.stdout
    assert "Entry Point: codey_cli.py" in res.stdout
    # launch with --message (documented path)
    res = _run_cli(["launch", "codey", "--message", "journey test"], env)
    out = res.stdout + res.stderr
    assert "codey" in out.lower() or "Code Search" in out or "SPINNER" in out
    assert "Entry Point" not in out
    assert "nameerror" not in out.lower() and "attributeerror" not in out.lower() and "unbound" not in out.lower()
    # list shows the priority entry
    res = _run_cli(["list"], env)
    assert res.returncode == 0
    assert "codey (entry: codey_cli.py)" in res.stdout or "codey_cli.py" in res.stdout

    # Expanded coverage: config (real add + list, verify side effect)
    res = _run_cli(
        [
            "config",
            "add",
            "--section",
            "llm",
            "--name",
            "journey_prof",
            "--json",
            '{"provider":"openai","model":"gpt-4o-mini","base_url":"https://api.openai.com/v1","api_key":"${OPENAI_API_KEY}"}',
        ],
        env,
    )
    assert res.returncode == 0
    assert "Added" in res.stdout
    res = _run_cli(["config", "list", "--section", "llm"], env)
    assert res.returncode == 0
    assert "journey_prof" in res.stdout

    # Expanded: wizard non-interactive (documented in guide) - verify file created
    wiz_dir = tmp_path / "journey-wiz"
    if wiz_dir.exists():
        shutil.rmtree(wiz_dir)
    wiz_dir.mkdir(parents=True, exist_ok=True)
    res = _run_cli(
        [
            "wizard",
            "--non-interactive",
            "-n",
            "JourneyTeam",
            "-r",
            "Lead:coord",
            "--no-shortcut",
            "--output-dir",
            str(wiz_dir),
        ],
        env,
    )
    assert res.returncode == 0
    assert "Team blueprint created" in res.stdout
    assert (wiz_dir / "journeyteam" / "blueprint_journeyteam.py").exists()

    # Expanded: add / delete / uninstall lifecycle - verify side effects
    add_src = wiz_dir / "journeyteam"
    res = _run_cli(["add", str(add_src), "--name", "journeyteam"], env)
    assert res.returncode == 0
    user_bp = data_root / "blueprints" / "journeyteam"
    assert user_bp.exists()
    res = _run_cli(["delete", "journeyteam"], env)
    assert res.returncode == 0
    assert not user_bp.exists()

    # complete lifecycle: install-executable then uninstall, assert gone
    res = _run_cli(["install-executable", "codey"], env)
    assert res.returncode == 0, res.stderr + res.stdout
    user_bin = data_root / "bin" / "codey"
    assert user_bin.exists()
    res = _run_cli(["uninstall", "codey"], env)
    assert res.returncode == 0
    assert not user_bin.exists()
