"""TDD for ``swarm-cli moa`` (dogfood path through Typer entry)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm.core.moa.cli import (
    GrokParticipantBackend,
    format_moa_text,
    parse_fake_responses,
    run_moa_cli,
)
from tests.xdg_isolation import run_swarm_cli


def test_parse_fake_responses_pairs_and_json():
    assert parse_fake_responses("a=one||b=two") == {"a": "one", "b": "two"}
    assert parse_fake_responses('{"x": "hi"}') == {"x": "hi"}
    with pytest.raises(ValueError, match=r"--fake-responses"):
        parse_fake_responses("noequals")
    with pytest.raises(ValueError, match=r"--fake-responses"):
        parse_fake_responses("{not-json")
    with pytest.raises(ValueError, match=r"--fake-responses"):
        parse_fake_responses('["not", "object"]')
    with pytest.raises(ValueError, match=r"--fake-responses"):
        parse_fake_responses("=missing-name")


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
    assert payload["mode"] == "consensus_only"
    assert payload["specialists"] == []
    assert payload["panel_wrote"] is False
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
):
    """Invoke Typer ``swarm-cli`` in a subprocess with isolated XDG dirs."""
    return run_swarm_cli(*args, xdg_root=xdg_root, overrides=env)


def test_swarm_cli_moa_subprocess_fake(tmp_path: Path):
    """Invoke the real Typer entrypoint as users do: python -m / swarm-cli moa.

    Non-team (no --act) is Path A: consensus_only via run_moa_consensus +
    team_result_to_payload (mode key + nested moa opinions).
    """
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
    assert data["mode"] == "consensus_only"
    # team_result_to_payload: top-level determination matches run_moa_cli object shape.
    assert isinstance(data["determination"], dict) and data["determination"].get("answer")
    assert data["specialists"] == []
    assert data["writes"] == []
    assert data["panel_wrote"] is False
    moa = data.get("moa") or {}
    opinions = moa.get("opinions") or []
    assert len(opinions) == 2
    assert all(o["permission_mode"] == "approve-reads" for o in opinions)


def test_swarm_cli_moa_consensus_only_json_mode(tmp_path: Path):
    """CLI Path A JSON contract: mode=consensus_only without --team/--act."""
    trace = tmp_path / "consensus_trace.json"
    proc = _swarm_cli(
        "moa",
        "Should we default public APIs to token-bucket rate limiting?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"yes token bucket at edge","confidence":0.9}'
        '||critic={"claim":"yes token bucket with metrics","confidence":0.85}',
        "--json",
        "--trace",
        str(trace),
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_only"
    assert data["question"] == (
        "Should we default public APIs to token-bucket rate limiting?"
    )
    assert isinstance(data["determination"], dict) and data["determination"].get("answer")
    assert data["specialists"] == []
    assert data["writes"] == []
    assert data["reads"] == []
    assert data["panel_wrote"] is False
    assert isinstance(data.get("final_preview"), str)
    assert data.get("backend") == "fake"
    assert data.get("participants") == ["analyst", "critic"]
    assert data.get("permission") == "approve-reads"
    moa = data["moa"]
    assert moa["backend"] == "fake"
    assert len(moa["opinions"]) == 2
    assert moa["act"] is None
    assert moa["writes"] == []
    assert isinstance(moa.get("determination"), dict)
    assert data["determination"]["answer"] == moa["determination"]["answer"]
    assert trace.is_file()
    traced = json.loads(trace.read_text(encoding="utf-8"))
    assert traced["mode"] == "consensus_only"
    assert traced["specialists"] == []
    assert traced["writes"] == []
    assert traced["panel_wrote"] is False
    assert data.get("trace_path") == str(trace)


def test_swarm_cli_moa_consensus_only_mode(tmp_path: Path):
    """Without --team, pure-path JSON is consensus_only (mirrors team mode asserts).

    ``swarm-cli moa … --json`` with no ``--team`` must expose mode /
    empty writes / empty specialists / panel_wrote=False (Path A parity).
    """
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
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_only"
    assert data["panel_wrote"] is False
    assert data["writes"] == []
    assert data["specialists"] == []
    opinions = (data.get("moa") or {}).get("opinions") or []
    assert len(opinions) == 2
    assert isinstance(data["determination"], dict) and data["determination"].get("answer")


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
    # Same object shape as plain moa --json so data["determination"]["answer"] works.
    assert isinstance(data["determination"], dict)
    answer = (data["determination"].get("answer") or "").lower()
    assert "ship" in answer or "token" in answer or data["determination"].get("answer")


def test_swarm_cli_moa_team_requires_workdir(tmp_path: Path):
    """--team without --workdir is a usage error (exit 2), not a crash."""
    proc = _swarm_cli(
        "moa", "q", "--backend", "fake", "--team", "--json", xdg_root=tmp_path / "xdg"
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--team" in err and "--workdir" in err
    assert "specialist" in err.lower() or "workspace" in err.lower()
    # Clarify --cwd is not a substitute (cwd vs workdir UX).
    assert "--cwd" in err


def test_swarm_cli_moa_rejects_flag_like_participant_names(tmp_path: Path):
    """--participants must not accept flag-like seat names (acpx argv injection)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--participants",
        "--approve-all,analyst",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = (proc.stderr + proc.stdout).lower()
    assert "participant" in err or "invalid" in err


def test_swarm_cli_moa_workdir_requires_team(tmp_path: Path):
    """--workdir without --team is a usage error; do not silently alias to --cwd.

    Exit code 2 documents the validation path (usage/validation).
    """
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--workdir",
        str(tmp_path / "ws"),
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--workdir" in err and "--team" in err
    assert "--cwd" in err
    # Must not have run MoA successfully as if workdir were cwd.
    assert "{" not in proc.stdout or "determination" not in proc.stdout.lower()


def test_swarm_cli_moa_team_blank_workdir_exit_2(tmp_path: Path):
    """Whitespace-only --workdir is treated as missing (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--team",
        "--workdir",
        "   ",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--workdir" in err


def test_swarm_cli_moa_team_empty_team_tasks_exit_2(tmp_path: Path):
    """Empty / pipe-only --team-tasks is a usage error (exit 2)."""
    ws = tmp_path / "empty_tasks_ws"
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "|||",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--team-tasks" in err
    # Must not silently default to implementer when user passed empty tasks.
    assert not (ws / "decision.md").exists()


def test_swarm_cli_moa_invalid_participant_name_exit_2(tmp_path: Path):
    """Flag-like --participants names are rejected as usage errors (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--participants",
        "ok,--approve-all",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--participants" in err
    assert "approve-all" in err or "leading" in err.lower()
    assert "MoA failed" not in err


def test_swarm_cli_moa_team_deny_all_permission(tmp_path: Path):
    """--team honors --permission deny-all for panelists (specialists still write)."""
    ws = tmp_path / "deny_ws"
    proc = _swarm_cli(
        "moa",
        "Ship carefully?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"ship","confidence":0.9}||critic={"claim":"ship","confidence":0.85}',
        "--permission",
        "deny-all",
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(proc.stdout.strip()[proc.stdout.strip().find("{") :])
    assert data["permission"] == "deny-all"
    assert data["panel_wrote"] is False
    moa = data.get("moa") or {}
    opinions = moa.get("opinions") or []
    assert opinions
    assert all(o.get("permission_mode") == "deny-all" for o in opinions)
    assert "decision.md" in data["writes"]
    assert (ws / "decision.md").is_file()


def test_swarm_cli_moa_team_rejects_approve_all(tmp_path: Path):
    """--team cannot loosen participant permissions to approve-all."""
    ws = tmp_path / "bad_perm_ws"
    proc = _swarm_cli(
        "moa",
        "Should we?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        "analyst=yes||critic=yes",
        "--permission",
        "approve-all",
        "--team",
        "--workdir",
        str(ws),
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 5, proc.stderr + proc.stdout
    err = (proc.stderr + proc.stdout).lower()
    assert "approve-all" in err or "read-only" in err or "refused" in err
    # Specialist workspace must not have been written after policy failure.
    assert not (ws / "decision.md").exists()


def test_swarm_cli_moa_rejects_approve_all_without_team(tmp_path: Path):
    """Non-team path also rejects approve-all (parity with team)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--participants",
        "a",
        "--fake-responses",
        "a=hi",
        "--permission",
        "approve-all",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 5, proc.stderr + proc.stdout
    assert "approve-all" in (proc.stderr + proc.stdout).lower() or "read-only" in (
        proc.stderr + proc.stdout
    ).lower()


def test_swarm_cli_moa_team_xor_act(tmp_path: Path):
    """--team and --act together is a usage error (exit 2)."""
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
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--team" in err and "--act" in err
    assert "mutually exclusive" in err.lower()


def test_swarm_cli_moa_empty_participants_exit_2(tmp_path: Path):
    """Empty / whitespace-only --participants is a usage error (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--participants",
        ",,,",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--participants" in err


def test_swarm_cli_moa_unknown_backend_exit_2(tmp_path: Path):
    """Unknown --backend is a usage error with actionable choices (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "codex",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--backend" in err
    assert "fake" in err and "grok" in err
    # Must not look like an unexpected crash
    assert "Traceback" not in err


def test_swarm_cli_moa_bad_fake_responses_exit_2(tmp_path: Path):
    """Malformed --fake-responses is a usage error naming the flag (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--fake-responses",
        "not-a-pair",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--fake-responses" in err
    assert "name=text" in err or "JSON" in err


def test_swarm_cli_moa_bad_fake_responses_json_exit_2(tmp_path: Path):
    """Broken JSON object for --fake-responses is a usage error (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--fake-responses",
        "{not-json",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--fake-responses" in err
    assert "JSON" in err or "parse" in err.lower()


def test_swarm_cli_moa_team_bad_fake_responses_exit_2(tmp_path: Path):
    """Team path surfaces the same --fake-responses usage error (exit 2)."""
    proc = _swarm_cli(
        "moa",
        "q",
        "--backend",
        "fake",
        "--fake-responses",
        "broken",
        "--team",
        "--workdir",
        str(tmp_path / "ws"),
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 2
    err = proc.stderr + proc.stdout
    assert "Error:" in err
    assert "--fake-responses" in err


def test_swarm_cli_moa_verbose_without_team_exits_0(tmp_path: Path):
    """-v without --team still runs consensus-only path and exits 0."""
    proc = _swarm_cli(
        "moa",
        "Should we rate-limit?",
        "--backend",
        "fake",
        "--participants",
        "alpha,beta",
        "--fake-responses",
        "alpha=Yes with token bucket.||beta=Yes; document the quota.",
        "-v",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = (proc.stdout + proc.stderr).lower()
    # Human text path (not --json): determination section present
    assert "determination" in out or "opinion" in out or "token" in out
    # Verbose INFO may land on stderr (moa.collect / moa.determine)
    # but must not crash platformdirs / XDG
    assert "permission denied" not in proc.stderr.lower()
    assert "broken" not in proc.stderr.lower() or "symlink" not in proc.stderr.lower()


def test_swarm_cli_moa_json_team_mode_text_fields(tmp_path: Path):
    """--json team mode exposes determination object + specialist text previews."""
    ws = tmp_path / "json_team_ws"
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
        "implementer:Apply decision|tester:Verify",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_then_team"
    assert data["question"] == "Ship rate limiting?"
    # Same determination object shape as plain moa --json / consensus_only.
    assert isinstance(data["determination"], dict)
    assert data["determination"].get("answer")
    for key in ("answer", "rationale", "participant_names", "analysis"):
        assert key in data["determination"]
    nested = (data.get("moa") or {}).get("determination")
    assert isinstance(nested, dict)
    assert data["determination"]["answer"] == nested["answer"]
    assert isinstance(data.get("final_preview"), str)
    assert isinstance(data["writes"], list)
    assert "decision.md" in data["writes"]
    assert "test_notes.md" in data["writes"]
    specs = data["specialists"]
    assert len(specs) == 2
    for s in specs:
        assert isinstance(s["persona"], str)
        assert isinstance(s["instruction"], str)
        assert isinstance(s["ok"], bool)
        assert s["ok"] is True
        assert isinstance(s.get("output_preview"), str)
        assert s["output_preview"]  # non-empty specialist output
    personas = {s["persona"] for s in specs}
    assert personas == {"implementer", "tester"}
    assert data["panel_wrote"] is False
    assert data.get("backend") == "fake"
    assert data.get("workdir") == str(ws)


def test_swarm_cli_moa_team_unusable_panel_exit_1(tmp_path: Path):
    """--team exits 1 when the panel is unusable (all seats ok=False)."""
    ws = tmp_path / "unusable_ws"
    proc = _swarm_cli(
        "moa",
        "Should we proceed?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        # Responses that do not cover seat names → every opinion ok=False.
        "--fake-responses",
        "unrelated=not used by seats",
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 1, proc.stderr + proc.stdout
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_then_team"
    assert data["specialists"] == []
    assert data["writes"] == []
    opinions = (data.get("moa") or {}).get("opinions") or []
    assert opinions and all(o.get("ok") is False for o in opinions)
    assert not (ws / "decision.md").exists()
    assert not (ws / "moa_determination.md").exists()


def test_swarm_cli_moa_team_specialist_ok_false_exit_1(tmp_path: Path):
    """--team exits 1 when a specialist returns ok=False (unknown purpose)."""
    ws = tmp_path / "spec_fail_ws"
    proc = _swarm_cli(
        "moa",
        "Ship carefully?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"ship","confidence":0.9}||critic={"claim":"ship","confidence":0.85}',
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply|wizard:Do magic",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 1, proc.stderr + proc.stdout
    out = proc.stdout.strip()
    start = out.find("{")
    assert start >= 0, out
    data = json.loads(out[start:])
    assert data["mode"] == "consensus_then_team"
    specs = {s["persona"]: s for s in data["specialists"]}
    assert specs["implementer"]["ok"] is True
    assert specs["wizard"]["ok"] is False
    assert "decision.md" in data["writes"]
    assert (ws / "decision.md").is_file()


def test_swarm_cli_moa_team_preserves_existing_notes(tmp_path: Path):
    """CLI seeds notes.txt only when missing; existing notes are not overwritten."""
    ws = tmp_path / "notes_ws"
    ws.mkdir(parents=True)
    notes = ws / "notes.txt"
    notes.write_text("KEEP ME — user context", encoding="utf-8")
    proc = _swarm_cli(
        "moa",
        "This question text must not clobber notes.txt",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"ship","confidence":0.9}||critic={"claim":"ship","confidence":0.85}',
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply",
        "--json",
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert notes.read_text(encoding="utf-8") == "KEEP ME — user context"
    # Implementer may embed notes; ensure preserved content is what was seeded.
    decision = (ws / "decision.md").read_text(encoding="utf-8")
    assert "KEEP ME" in decision
    assert "must not clobber" not in notes.read_text(encoding="utf-8")


def test_swarm_cli_moa_trace_creates_parent_dirs(tmp_path: Path):
    """--trace creates missing parent directories (team and consensus paths)."""
    ws = tmp_path / "trace_ws"
    nested = tmp_path / "deep" / "nested" / "dir" / "team_trace.json"
    assert not nested.parent.exists()
    proc = _swarm_cli(
        "moa",
        "Ship?",
        "--backend",
        "fake",
        "--participants",
        "analyst,critic",
        "--fake-responses",
        'analyst={"claim":"ship","confidence":0.9}||critic={"claim":"ship","confidence":0.85}',
        "--team",
        "--workdir",
        str(ws),
        "--team-tasks",
        "implementer:Apply",
        "--json",
        "--trace",
        str(nested),
        xdg_root=tmp_path / "xdg",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert nested.is_file()
    traced = json.loads(nested.read_text(encoding="utf-8"))
    assert traced["mode"] == "consensus_then_team"
    assert traced.get("trace_path") == str(nested)

    consensus_trace = tmp_path / "other" / "deep" / "consensus_trace.json"
    assert not consensus_trace.parent.exists()
    proc2 = _swarm_cli(
        "moa",
        "Rate limit?",
        "--backend",
        "fake",
        "--participants",
        "alpha,beta",
        "--fake-responses",
        "alpha=Yes.||beta=Yes with metrics.",
        "--json",
        "--trace",
        str(consensus_trace),
        xdg_root=tmp_path / "xdg2",
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    assert consensus_trace.is_file()
    traced2 = json.loads(consensus_trace.read_text(encoding="utf-8"))
    assert traced2["mode"] == "consensus_only"


def test_configure_moa_verbose_logging_does_not_force_root():
    """Verbose setup must not wipe root handlers (no basicConfig force=True)."""
    import logging

    from swarm.core.swarm_cli import configure_moa_verbose_logging

    root = logging.getLogger()
    moa_log = logging.getLogger("swarm.core.moa")
    sentinel = logging.NullHandler()
    root.addHandler(sentinel)
    # Reset any prior verbose configuration from other tests.
    prior_handlers = list(moa_log.handlers)
    prior_propagate = moa_log.propagate
    prior_marker = getattr(moa_log, "_swarm_moa_cli_verbose", False)
    moa_log.handlers.clear()
    setattr(moa_log, "_swarm_moa_cli_verbose", False)
    moa_log.propagate = True
    try:
        configure_moa_verbose_logging()
        configure_moa_verbose_logging()  # idempotent
        assert sentinel in root.handlers
        assert moa_log.level == logging.INFO
        assert moa_log.propagate is False
        assert getattr(moa_log, "_swarm_moa_cli_verbose") is True
        assert sum(isinstance(h, logging.StreamHandler) for h in moa_log.handlers) == 1
        # Source contract: moa command must not use basicConfig(force=True).
        import inspect

        from swarm.core import swarm_cli as swarm_cli_mod

        src = inspect.getsource(swarm_cli_mod.moa)
        assert "basicConfig" not in src
        assert "force=True" not in src
    finally:
        root.removeHandler(sentinel)
        moa_log.handlers.clear()
        for h in prior_handlers:
            moa_log.addHandler(h)
        moa_log.propagate = prior_propagate
        setattr(moa_log, "_swarm_moa_cli_verbose", prior_marker)
