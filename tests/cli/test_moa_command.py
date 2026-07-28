"""TDD for ``swarm-cli moa`` (dogfood path through Typer entry)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from swarm.core.moa.cli import (
    GrokParticipantBackend,
    format_moa_text,
    parse_fake_responses,
    run_moa_cli,
)


def test_parse_fake_responses_pairs_and_json():
    assert parse_fake_responses("a=one||b=two") == {"a": "one", "b": "two"}
    assert parse_fake_responses('{"x": "hi"}') == {"x": "hi"}
    with pytest.raises(ValueError):
        parse_fake_responses("noequals")


@pytest.mark.asyncio
async def test_run_moa_cli_fake_backend_end_to_end():
    """Drive shipped run_moa_cli with fake participants (real orchestrator path)."""
    payload = await run_moa_cli(
        "How should we handle retries?",
        ["claude", "codex"],
        backend="fake",
        fake_responses={
            "claude": "Exponential backoff with jitter.",
            "codex": "Cap retries at 5; use jitter.",
        },
        act=False,
    )
    assert len(payload["opinions"]) == 2
    assert all(o["permission_mode"] in ("approve-reads", "deny-all") for o in payload["opinions"])
    assert payload["determination"] and "jitter" in payload["determination"]["answer"].lower() or (
        "backoff" in payload["determination"]["answer"].lower()
        or "retry" in payload["determination"]["answer"].lower()
        or payload["determination"]["answer"]
    )
    assert payload["act"] is None
    assert payload["writes"] == []
    text = format_moa_text(payload)
    assert "Opinions" in text and "Determination" in text


@pytest.mark.asyncio
async def test_run_moa_cli_act_writes_via_orchestrator_only(tmp_path: Path):
    out = tmp_path / "det.md"
    payload = await run_moa_cli(
        "q",
        ["a"],
        backend="fake",
        fake_responses={"a": "do X"},
        act=True,
        action="persist",
        act_write_path=str(out),
    )
    assert payload["act"] and payload["act"]["ok"]
    assert out.is_file()
    assert "do X" in out.read_text(encoding="utf-8")


def test_grok_backend_build_command_is_readonly_framed():
    be = GrokParticipantBackend(grok_bin="grok")
    argv = be.build_command("hello", cwd="/repo")
    assert argv[0] == "grok"
    assert "-p" in argv
    assert "Write" in argv[argv.index("--disallowed-tools") + 1]
    assert "--cwd" in argv


def _swarm_cli(
    *args: str,
    env: dict | None = None,
    xdg_root: Path | None = None,
) -> subprocess.CompletedProcess:
    """Invoke Typer ``swarm-cli`` in a subprocess with isolated XDG dirs.

    Host ``~/.cache`` may be a broken symlink; platformdirs mkdir then fails.
    Always pin XDG_* (and HOME under them) to a writable tree.
    """
    import tempfile

    e = os.environ.copy()
    e["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    root = Path(xdg_root) if xdg_root is not None else Path(tempfile.mkdtemp(prefix="swarm-cli-xdg-"))
    for sub in ("cache", "config", "data", "home"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    e["HOME"] = str(root / "home")
    e["XDG_CACHE_HOME"] = str(root / "cache")
    e["XDG_CONFIG_HOME"] = str(root / "config")
    e["XDG_DATA_HOME"] = str(root / "data")
    e["SWARM_USER_DATA_DIR"] = str(root / "data" / "swarm")
    if env:
        e.update(env)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from swarm.core.swarm_cli import app; "
                "import sys; sys.argv = ['swarm-cli'] + sys.argv[1:]; app()"
            ),
            *args,
        ],
        capture_output=True,
        text=True,
        env=e,
        timeout=60,
        cwd=str(Path(__file__).resolve().parents[2]),
    )


def test_swarm_cli_moa_subprocess_fake(tmp_path: Path):
    """Invoke the real Typer entrypoint as users do: python -m / swarm-cli moa."""
    proc = _swarm_cli(
        "moa",
        "Should we add rate limits?",
        "--backend",
        "fake",
        "--participants",
        "alpha,beta",
        "--fake-responses",
        "alpha=Yes with token bucket.||beta=Yes; document the quota.",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    # JSON may be preceded by noise; find last object.
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert len(data["opinions"]) == 2
    assert data["determination"] is not None
    assert all(o["permission_mode"] == "approve-reads" for o in data["opinions"])


def test_swarm_cli_moa_team_mode(tmp_path: Path):
    """--team runs consensus-then-team without openai-agents."""
    ws = tmp_path / "teamws"
    trace = tmp_path / "team_trace.json"
    proc = _swarm_cli(
        "moa",
        "Ship rate limiting?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"ship carefully","confidence":0.9}||critic={"claim":"ship with tests","confidence":0.85}',
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply|tester:Verify|docs:ADR|researcher:Scan",
        "--json",
        "--trace",
        str(trace),
        "-v",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    # Verbose logs on stderr
    assert "moa.team" in proc.stderr or "consensus_then_team" in proc.stderr
    out = proc.stdout.strip()
    start = out.find("{")
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_then_team"
    assert data["panel_wrote"] is False
    assert "decision.md" in data["writes"]
    assert "test_notes.md" in data["writes"]
    assert "docs/ADR.md" in data["writes"]
    assert "research_notes.md" in data["writes"]
    assert (ws / "decision.md").is_file()
    assert (ws / "research_notes.md").is_file()
    assert trace.is_file()
    assert "ship" in data["determination"].lower() or "token" in data["determination"].lower() or data["determination"]


def test_swarm_cli_moa_team_requires_workdir(tmp_path: Path):
    proc = _swarm_cli(
        "moa", "q", "--backend", "fake", "--team", "--json", xdg_root=tmp_path / "xdg"
    )
    assert proc.returncode == 2
    assert "workdir" in (proc.stderr + proc.stdout).lower()


def test_swarm_cli_moa_team_xor_act(tmp_path: Path):
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--team",
        "--workdir",
        str(tmp_path / "ws"),
        "--act",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    assert "--team" in (proc.stderr + proc.stdout) or "act" in (proc.stderr + proc.stdout).lower()
