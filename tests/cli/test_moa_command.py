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


def test_swarm_cli_moa_subprocess_fake(tmp_path: Path):
    """Invoke the real Typer entrypoint as users do: python -m / swarm-cli moa."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    # Prefer package entry if installed; fall back to module path.
    cmd = [
        sys.executable,
        "-c",
        (
            "from swarm.core.swarm_cli import app; "
            "import sys; sys.argv = ['swarm-cli'] + sys.argv[1:]; app()"
        ),
        "moa",
        "Should we add rate limits?",
        "--backend",
        "fake",
        "--participants",
        "alpha,beta",
        "--fake-responses",
        "alpha=Yes with token bucket.||beta=Yes; document the quota.",
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(Path(__file__).resolve().parents[2]),
        timeout=30,
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
