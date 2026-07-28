"""Pure MoA team runner: consensus only vs consensus-then-team (no openai-agents)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from swarm.core.moa.policy import WriteDeniedError
from swarm.core.moa.team import (
    TEAM_CLI_ENVELOPE_KEYS,
    TEAM_RESULT_PAYLOAD_KEYS,
    TeamTask,
    default_output_path,
    format_team_text,
    parse_team_tasks,
    run_moa_consensus,
    run_moa_then_team,
    team_result_to_payload,
    validate_team_payload,
)
from swarm.core.moa.types import PermissionMode

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_ASSETS = (
    _REPO_ROOT / "docs" / "examples" / "moa-consensus-vs-team" / "assets"
)


def test_team_apis_exported_from_package_toplevel():
    """Public MoA team surface is re-exported from swarm.core.moa (not only .team)."""
    import swarm.core.moa as moa
    from swarm.core.moa import (
        TeamTask as PkgTeamTask,
        format_team_text as pkg_format_team_text,
        parse_team_tasks as pkg_parse_team_tasks,
        run_moa_consensus as pkg_run_moa_consensus,
        run_moa_then_team as pkg_run_moa_then_team,
        team_result_to_payload as pkg_team_result_to_payload,
        validate_team_payload as pkg_validate_team_payload,
    )

    names = (
        "TeamTask",
        "parse_team_tasks",
        "run_moa_consensus",
        "run_moa_then_team",
        "format_team_text",
        "team_result_to_payload",
        "validate_team_payload",
        "TEAM_RESULT_PAYLOAD_KEYS",
        "SPECIALIST_PAYLOAD_KEYS",
        "MOA_NESTED_PAYLOAD_KEYS",
        "TEAM_CLI_ENVELOPE_KEYS",
    )
    for name in names:
        assert name in moa.__all__
        assert hasattr(moa, name)

    assert PkgTeamTask is TeamTask
    assert pkg_parse_team_tasks is parse_team_tasks
    assert pkg_run_moa_consensus is run_moa_consensus
    assert pkg_run_moa_then_team is run_moa_then_team
    assert pkg_format_team_text is format_team_text
    assert pkg_validate_team_payload is validate_team_payload
    assert pkg_team_result_to_payload is team_result_to_payload


@pytest.mark.asyncio
async def test_run_moa_consensus_only_no_writes():
    result = await run_moa_consensus(
        "Should we rate-limit?",
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes with metrics","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_only"
    assert "token bucket" in result.determination.lower() or "yes" in result.determination.lower()
    assert result.specialist_results == []
    assert result.writes == []
    # Real panel act surface (not tautological panel_wrote property).
    assert (result.moa_payload.get("writes") or []) == []
    assert result.panel_wrote is False  # documentation-only on MoATeamResult
    # Payload still has panel opinions
    opinions = result.moa_payload.get("opinions") or []
    assert len(opinions) == 2
    assert all(o.get("permission_mode") == "approve-reads" for o in opinions)


@pytest.mark.asyncio
async def test_team_path_approve_reads_and_deny_all(tmp_path: Path):
    """Team path threads participant permission; both read-only modes work."""
    fakes = {
        "analyst": '{"claim":"yes","confidence":0.9}',
        "critic": '{"claim":"yes","confidence":0.8}',
    }
    for mode in (
        PermissionMode.APPROVE_READS.value,
        PermissionMode.DENY_ALL.value,
        PermissionMode.APPROVE_READS,
        PermissionMode.DENY_ALL,
    ):
        only = await run_moa_consensus(
            "q",
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission=mode,
        )
        expected = mode.value if isinstance(mode, PermissionMode) else mode
        assert only.moa_payload.get("permission") == expected
        opinions = only.moa_payload.get("opinions") or []
        assert opinions
        assert all(o.get("permission_mode") == expected for o in opinions)

        team = await run_moa_then_team(
            tmp_path / f"ws_{expected}_{id(mode)}",
            "q",
            specialist_tasks=[TeamTask("implementer", "apply", "decision.md")],
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission=mode,
        )
        assert team.mode == "consensus_then_team"
        assert team.panel_wrote is False
        assert team.moa_payload.get("permission") == expected
        team_ops = team.moa_payload.get("opinions") or []
        assert all(o.get("permission_mode") == expected for o in team_ops)
        # Specialists still write; only panelists are permission-locked.
        assert "decision.md" in team.writes


@pytest.mark.asyncio
async def test_team_path_rejects_approve_all(tmp_path: Path):
    """Team path must not loosen participants to approve-all (same as panel path)."""
    fakes = {
        "analyst": '{"claim":"yes","confidence":0.9}',
        "critic": '{"claim":"yes","confidence":0.8}',
    }
    with pytest.raises(WriteDeniedError, match="read-only|approve-all|refused"):
        await run_moa_consensus(
            "q",
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission=PermissionMode.APPROVE_ALL,
        )
    with pytest.raises(WriteDeniedError, match="read-only|approve-all|refused"):
        await run_moa_consensus(
            "q",
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission="approve-all",
        )
    with pytest.raises(WriteDeniedError):
        await run_moa_then_team(
            tmp_path / "approve_all_ws",
            "q",
            specialist_tasks=[TeamTask("implementer", "apply", "decision.md")],
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission="approve-all",
        )
    with pytest.raises(WriteDeniedError):
        await run_moa_then_team(
            tmp_path / "write_mode_ws",
            "q",
            moa_backend="fake",
            moa_fake_responses=fakes,
            permission="write",
        )
    # Policy fails before specialist materialization.
    assert not (tmp_path / "approve_all_ws" / "decision.md").exists()
    assert not (tmp_path / "write_mode_ws" / "decision.md").exists()


@pytest.mark.asyncio
async def test_run_moa_then_team_multi_specialists(tmp_path: Path):
    ws = tmp_path / "team"
    result = await run_moa_then_team(
        ws,
        "Should we enable edge rate limiting?",
        specialist_tasks=[
            TeamTask("implementer", "Write the decision", "decision.md"),
            TeamTask("tester", "Draft verification", "test_notes.md"),
            TeamTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_then_team"
    assert "token bucket" in result.determination.lower()
    assert {s.persona for s in result.specialist_results} == {
        "implementer",
        "tester",
        "docs",
    }
    assert all(s.ok for s in result.specialist_results)
    assert (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    assert (ws / "test_notes.md").is_file()
    assert (ws / "docs" / "ADR.md").is_file()
    assert "decision.md" in result.writes
    # Footer documents pure path (not openai-agents)
    body = (ws / "decision.md").read_text(encoding="utf-8")
    assert "openai-agents" not in body.lower() or "no openai-agents" in body.lower()
    assert result.panel_wrote is False


@pytest.mark.asyncio
async def test_consensus_vs_team_contrast(tmp_path: Path):
    """Same question: consensus-only has no files; team path materializes artifacts."""
    q = "Ship rate limiting?"
    fakes = {
        "analyst": '{"claim":"ship carefully","confidence":0.9}',
        "critic": '{"claim":"ship carefully with tests","confidence":0.85}',
    }
    only = await run_moa_consensus(
        q, moa_backend="fake", moa_fake_responses=fakes
    )
    team = await run_moa_then_team(
        tmp_path / "ws",
        q,
        specialist_tasks=[
            TeamTask("implementer", "apply", "decision.md"),
            TeamTask("tester", "verify", "test_notes.md"),
        ],
        moa_backend="fake",
        moa_fake_responses=fakes,
    )
    assert only.mode == "consensus_only" and only.writes == []
    assert team.mode == "consensus_then_team"
    assert "decision.md" in team.writes
    assert "test_notes.md" in team.writes
    # Panel act surface empty on both paths (real writes live on moa_payload).
    assert (only.moa_payload.get("writes") or []) == []
    assert (team.moa_payload.get("writes") or []) == []
    # Both share a non-empty determination from the same fake panel
    assert only.determination
    assert team.determination


def test_parse_team_tasks_string_and_at_path():
    tasks = parse_team_tasks(
        "implementer:Apply|tester:Verify@qa/notes.md|docs|researcher:scan"
    )
    assert tasks is not None
    by = {t.purpose: t for t in tasks}
    assert by["implementer"].output_path == "decision.md"
    assert by["tester"].output_path == "qa/notes.md"
    assert by["docs"].output_path == "docs/ADR.md"
    assert by["researcher"].instruction == "scan"
    assert parse_team_tasks("") is None
    assert parse_team_tasks(None) is None


def test_parse_team_tasks_normalizes_backslash_paths():
    """Windows-style paths become POSIX-relative keys at parse time."""
    # Raw strings use a single backslash (Windows separator), not an escaped pair.
    tasks = parse_team_tasks(r"docs:Write ADR@docs\ADR.md|tester:Verify@qa\notes.md")
    assert tasks is not None
    by = {t.purpose: t for t in tasks}
    assert by["docs"].output_path == "docs/ADR.md"
    assert by["tester"].output_path == "qa/notes.md"

    from_list = parse_team_tasks(
        [
            {"purpose": "implementer", "instruction": "x", "output_path": r"out\dec.md"},
            TeamTask("docs", "ADR", r"docs\ADR.md"),
        ]
    )
    assert from_list is not None
    assert from_list[0].output_path == "out/dec.md"
    assert from_list[1].output_path == "docs/ADR.md"



def test_parse_team_tasks_at_path_bare_filename():
    tasks = parse_team_tasks("implementer:Apply@out.md|docs@docs/custom.md")
    assert tasks is not None
    assert tasks[0].instruction == "Apply"
    assert tasks[0].output_path == "out.md"
    assert tasks[1].purpose == "docs"
    assert tasks[1].output_path == "docs/custom.md"


def test_parse_team_tasks_email_then_explicit_path():
    """Last @ wins: earlier @ (e.g. email local-part) stay in the instruction."""
    tasks = parse_team_tasks("implementer:cc user@ex.com@artifacts/decision.md")
    assert tasks is not None
    assert tasks[0].instruction == "cc user@ex.com"
    assert tasks[0].output_path == "artifacts/decision.md"


def test_parse_team_tasks_list_and_dict_forms():
    as_list = parse_team_tasks(
        [
            "implementer:Apply@x.md",
            {"purpose": "tester", "instruction": "verify", "output_path": "t.md"},
            TeamTask("docs", "adr", "docs/A.md"),
        ]
    )
    assert as_list is not None
    assert [t.purpose for t in as_list] == ["implementer", "tester", "docs"]
    assert as_list[0].output_path == "x.md"
    assert as_list[1].output_path == "t.md"
    assert as_list[2].output_path == "docs/A.md"

    # Top-level also accepts a single dict or TeamTask
    single = parse_team_tasks({"purpose": "researcher", "instruction": "scan"})
    assert single is not None and len(single) == 1
    assert single[0].output_path == "research_notes.md"

    one_task = TeamTask("implementer", "go", "y.md")
    assert parse_team_tasks(one_task) == [one_task]


@pytest.mark.asyncio
async def test_parse_at_path_roundtrip_writes(tmp_path: Path):
    """Parsed @path tasks actually materialize at the custom locations."""
    tasks = parse_team_tasks(
        "implementer:Apply@custom/decision.md|tester:Check@custom/qa.md"
    )
    result = await run_moa_then_team(
        tmp_path / "ws",
        "Ship?",
        specialist_tasks=tasks,
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.85}',
        },
    )
    assert all(s.ok for s in result.specialist_results)
    assert (tmp_path / "ws" / "custom" / "decision.md").is_file()
    assert (tmp_path / "ws" / "custom" / "qa.md").is_file()


def test_parse_team_tasks_list_of_dicts():
    tasks = parse_team_tasks(
        [
            {"purpose": "implementer", "instruction": "Apply", "output_path": "out/dec.md"},
            {"purpose": "tester"},  # defaults instruction + output_path
            {"instruction": "orphan"},  # purpose defaults to implementer
        ]
    )
    assert tasks is not None
    assert len(tasks) == 3
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "Apply"
    assert tasks[0].output_path == "out/dec.md"
    assert tasks[1].purpose == "tester"
    assert tasks[1].instruction == "tester"
    assert tasks[1].output_path == "test_notes.md"
    assert tasks[2].purpose == "implementer"
    assert tasks[2].instruction == "orphan"
    assert tasks[2].output_path == "decision.md"


def test_parse_team_tasks_list_of_team_task_objects():
    original = [
        TeamTask("docs", "Write ADR", "docs/ADR.md"),
        TeamTask("researcher", "scan", "research_notes.md"),
    ]
    tasks = parse_team_tasks(original)
    assert tasks is not None
    assert len(tasks) == 2
    assert tasks[0] is original[0]
    assert tasks[1].purpose == "researcher"
    assert tasks[1].output_path == "research_notes.md"


def test_parse_team_tasks_nested_string_in_list():
    tasks = parse_team_tasks(
        [
            "implementer:Apply|tester:Verify@qa.md",
            TeamTask("docs", "ADR", "docs/ADR.md"),
            {"purpose": "researcher", "instruction": "Inventory"},
        ]
    )
    assert tasks is not None
    purposes = [t.purpose for t in tasks]
    assert purposes == ["implementer", "tester", "docs", "researcher"]
    assert tasks[0].instruction == "Apply"
    assert tasks[1].output_path == "qa.md"
    assert tasks[3].output_path == "research_notes.md"


def test_parse_team_tasks_empty_parts_with_pipes():
    """Empty segments from leading/trailing/double pipes are skipped."""
    tasks = parse_team_tasks("||implementer:Apply||tester:Verify@qa.md||")
    assert tasks is not None
    assert len(tasks) == 2
    assert tasks[0].purpose == "implementer"
    assert tasks[1].purpose == "tester"
    assert tasks[1].output_path == "qa.md"
    # Only empty / whitespace parts → [] (explicit zero specialists, not missing)
    assert parse_team_tasks("|||") == []
    assert parse_team_tasks("  |  |  ") == []
    assert parse_team_tasks([]) == []


# hypothesis is not a project dependency (see pyproject.toml [project.optional-dependencies]);
# these parametrized edge cases stand in for property-based coverage of
# "never throws on random strings" and "purposes/instructions stripped".
@pytest.mark.parametrize(
    "raw",
    [
        "!!!",
        "::::",
        "@@@",
        "a:b:c:d@e@f",
        " purpose : instr @ path ",
        "\t\nimplementer:\nApply\n",
        "🔥:emoji@path/x.md",
        "solo",
        "x:",
        ":only-instruction",
        "p:i@",
        "@just-path",
        "a|b|c",
        "|||weird|||stuff|||",
        "tester:Verify@qa/notes.md|docs",
        "implementer:line1\nline2",
        "researcher:scan@out/notes.md@extra",
        "  ",
        "\n|\t|",
        "purpose only with spaces   ",
        "impl:instr with | pipe literal? no — split first",
        "A" * 200 + ":" + "B" * 200,
        "0:1@2",
        "mixed:instr@path/with spaces.md",
        "unknown:do stuff",
        "docs:ADR@docs/ADR.md|tester",
        # non-string / non-list shapes must not raise
        0,
        42,
        3.14,
        True,
        object(),
        {"purpose": "implementer"},
        ("implementer:Apply",),
    ],
)
def test_parse_team_tasks_never_raises_on_randomish_input(raw):
    """parse_team_tasks must not throw on arbitrary / malformed inputs."""
    result = parse_team_tasks(raw)  # type: ignore[arg-type]
    assert result is None or (
        isinstance(result, list) and all(isinstance(t, TeamTask) for t in result)
    )


@pytest.mark.parametrize(
    "raw,expected_purposes",
    [
        ("  implementer  :Apply", ["implementer"]),
        ("\ttester\t:Verify", ["tester"]),
        ("  docs  ", ["docs"]),
        ("  researcher  :scan@notes.md", ["researcher"]),
        ("  implementer :A |  tester :B ", ["implementer", "tester"]),
        ("\nimplementer\n:\nGo\n", ["implementer"]),
        ("  custom  :do it", ["custom"]),
        (" purpose with spaces :instr", ["purpose with spaces"]),
    ],
)
def test_parse_team_tasks_purposes_stripped(raw, expected_purposes):
    """String-form purpose tokens are .strip()'d; whitespace must not leak."""
    tasks = parse_team_tasks(raw)
    assert tasks is not None
    assert [t.purpose for t in tasks] == expected_purposes
    for t in tasks:
        assert t.purpose == t.purpose.strip()
        assert not t.purpose.startswith((" ", "\t", "\n"))
        assert not t.purpose.endswith((" ", "\t", "\n"))


@pytest.mark.parametrize(
    "raw,purpose,instruction,output_path",
    [
        ("implementer:Apply", "implementer", "Apply", "decision.md"),
        ("  implementer  :  Apply  ", "implementer", "Apply", "decision.md"),
        ("tester:Verify@qa/notes.md", "tester", "Verify", "qa/notes.md"),
        ("  tester : Verify @ qa/notes.md  ", "tester", "Verify", "qa/notes.md"),
        ("docs", "docs", "docs", "docs/ADR.md"),
        ("  docs  ", "docs", "docs", "docs/ADR.md"),
        ("researcher:scan", "researcher", "scan", "research_notes.md"),
        ("x:", "x", "x", None),  # empty instruction falls back to purpose
        ("p:i@", "p", "i", None),  # empty path after @ → default (none for "p")
        ("unknown:do", "unknown", "do", None),
        ("implementer:@path.md", "implementer", "implementer", "path.md"),
        # first ":" splits purpose; last "@" delimits path only when path-like
        ("a:b:c@d", "a", "b:c@d", None),  # bare "d" is not path-like
        ("a:b@c@d", "a", "b@c@d", None),
        ("a:b@c@out/d.md", "a", "b@c", "out/d.md"),
        ("a:b:c@out/d.md", "a", "b:c", "out/d.md"),
        # emails/handles stay in instruction; purpose default path applies
        (
            "implementer:ping user@example.com",
            "implementer",
            "ping user@example.com",
            "decision.md",
        ),
        # last path-like @ wins when email + explicit path
        (
            "implementer:cc user@ex.com@artifacts/decision.md",
            "implementer",
            "cc user@ex.com",
            "artifacts/decision.md",
        ),
        ("tester:Verify@notes.md", "tester", "Verify", "notes.md"),
        ("tester:Verify@notes.txt", "tester", "Verify", "notes.txt"),
        # spaces in paths are preserved
        (
            "implementer:Apply@out/path with spaces.md",
            "implementer",
            "Apply",
            "out/path with spaces.md",
        ),
        # parent-escape paths are preserved at parse time (WorkspaceTools blocks later)
        (
            "implementer:x@../../etc/passwd",
            "implementer",
            "x",
            "../../etc/passwd",
        ),
    ],
)
def test_parse_team_tasks_edge_shapes(raw, purpose, instruction, output_path):
    """Concrete edge shapes for colon / last-@ path grammar."""
    tasks = parse_team_tasks(raw)
    assert tasks is not None and len(tasks) == 1
    t = tasks[0]
    assert t.purpose == purpose
    assert t.instruction == instruction
    assert t.output_path == output_path


@pytest.mark.parametrize(
    "raw",
    [
        ":only",
        ":",
        "  :  instr  ",
        "  :  ",
        ":@path.md",
    ],
)
def test_parse_team_tasks_empty_purpose_segments_dropped(raw):
    """Empty purpose after strip is dropped → [] (explicit zero, not missing)."""
    assert parse_team_tasks(raw) == []


def test_parse_team_tasks_instructions_and_paths_stripped():
    """Instruction and @output_path are stripped like purpose."""
    tasks = parse_team_tasks("implementer:  Apply decision  @  out/dec.md  ")
    assert tasks is not None and len(tasks) == 1
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "Apply decision"
    assert tasks[0].output_path == "out/dec.md"

    multi = parse_team_tasks("  docs  :  Write ADR  |  tester  :  Verify  @  qa.md  ")
    assert multi is not None
    assert [t.purpose for t in multi] == ["docs", "tester"]
    assert multi[0].instruction == "Write ADR"
    assert multi[0].output_path == "docs/ADR.md"
    assert multi[1].instruction == "Verify"
    assert multi[1].output_path == "qa.md"


def test_parse_team_tasks_list_dict_purpose_defaults():
    """List-of-dicts edges: empty purpose falls back; purposes stripped; missing keys ok."""
    tasks = parse_team_tasks(
        [
            {},
            {"purpose": "", "instruction": "via-default-purpose"},
            {"purpose": "  spaced  ", "instruction": "keep"},
            {"purpose": "tester", "instruction": "", "output_path": ""},
        ]
    )
    assert tasks is not None
    assert len(tasks) == 4
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "implementer"
    assert tasks[0].output_path == "decision.md"
    assert tasks[1].purpose == "implementer"  # empty purpose → "implementer"
    assert tasks[1].instruction == "via-default-purpose"
    assert tasks[2].purpose == "spaced"  # dict form strips purpose
    assert tasks[2].instruction == "keep"
    assert tasks[3].purpose == "tester"
    assert tasks[3].instruction == "tester"  # empty instruction → purpose
    assert tasks[3].output_path == "test_notes.md"  # empty path → default

    # single dict / TeamTask also accepted at top level
    one = parse_team_tasks({"purpose": "  docs  ", "instruction": "  ADR  "})
    assert one is not None and len(one) == 1
    assert one[0].purpose == "docs"
    assert one[0].instruction == "ADR"
    assert one[0].output_path == "docs/ADR.md"

    tt = TeamTask("researcher", "scan", "research_notes.md")
    assert parse_team_tasks(tt) == [tt]

@pytest.mark.asyncio
async def test_unknown_specialist_purpose_ok_false(tmp_path: Path):
    result = await run_moa_then_team(
        tmp_path / "unk",
        "Should we?",
        specialist_tasks=[
            TeamTask("wizard", "cast spell", "spell.md"),
            TeamTask("implementer", "apply", "decision.md"),
        ],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.8}',
        },
    )
    by = {s.persona: s for s in result.specialist_results}
    assert by["wizard"].ok is False
    assert "unknown specialist purpose" in by["wizard"].output
    assert "implementer" in by["wizard"].output or "known" in by["wizard"].output
    assert by["implementer"].ok is True
    assert (tmp_path / "unk" / "decision.md").is_file()
    assert not (tmp_path / "unk" / "spell.md").is_file()


def test_default_output_path_single_source():
    """Parse defaults, helper, and known purposes share one map (no path drift)."""
    expected = {
        "implementer": "decision.md",
        "tester": "test_notes.md",
        "docs": "docs/ADR.md",
        "researcher": "research_notes.md",
    }
    for purpose, path in expected.items():
        assert default_output_path(purpose) == path
        assert default_output_path(purpose.upper()) == path
        assert default_output_path(f"  {purpose}  ") == path
    assert default_output_path("wizard") is None
    assert default_output_path("") is None

    # parse string + dict forms resolve via the same helper
    parsed = parse_team_tasks("implementer|tester|docs|researcher")
    assert parsed is not None
    assert [t.output_path for t in parsed] == list(expected.values())
    as_dicts = parse_team_tasks(
        [{"purpose": p, "instruction": p} for p in expected]
    )
    assert as_dicts is not None
    assert [t.output_path for t in as_dicts] == list(expected.values())


@pytest.mark.asyncio
async def test_default_specialist_when_tasks_none(tmp_path: Path):
    """specialist_tasks=None → single implementer writing decision.md."""
    ws = tmp_path / "default_impl"
    result = await run_moa_then_team(
        ws,
        "Ship it?",
        specialist_tasks=None,
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"ship carefully","confidence":0.9}',
            "critic": '{"claim":"ship carefully","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_then_team"
    assert len(result.specialist_results) == 1
    s = result.specialist_results[0]
    assert s.persona == "implementer"
    assert s.ok is True
    assert "Apply the MoA determination" in s.instruction
    impl_path = default_output_path("implementer")
    assert impl_path is not None
    assert (ws / impl_path).is_file()
    assert impl_path in result.writes
    body = (ws / impl_path).read_text(encoding="utf-8")
    assert "MoA consensus" in body or "Decision" in body


@pytest.mark.asyncio
async def test_empty_specialist_tasks_skips_default_implementer(tmp_path: Path):
    """specialist_tasks=[] means zero specialists — never alias to default implementer."""
    ws = tmp_path / "empty_specs"
    result = await run_moa_then_team(
        ws,
        "Consensus only via empty team list?",
        specialist_tasks=[],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_then_team"
    assert result.specialist_results == []
    impl_path = default_output_path("implementer")
    assert impl_path is not None
    assert impl_path not in result.writes
    assert not (ws / impl_path).exists()
    # Orchestrator-owned determination artifact is independent of specialists.
    assert (ws / "moa_determination.md").is_file()


@pytest.mark.asyncio
async def test_specialist_none_output_path_uses_default_helper(tmp_path: Path):
    """_run_specialist falls back via default_output_path, not hardcoded literals."""
    ws = tmp_path / "none_paths"
    fakes = {
        "analyst": '{"claim":"yes","confidence":0.9}',
        "critic": '{"claim":"yes","confidence":0.85}',
    }
    result = await run_moa_then_team(
        ws,
        "Ship?",
        specialist_tasks=[
            TeamTask("implementer", "apply", None),
            TeamTask("tester", "verify", None),
            TeamTask("docs", "adr", None),
            TeamTask("researcher", "scan", None),
        ],
        moa_backend="fake",
        moa_fake_responses=fakes,
    )
    assert all(s.ok for s in result.specialist_results)
    for purpose in ("implementer", "tester", "docs", "researcher"):
        path = default_output_path(purpose)
        assert path is not None
        assert path in result.writes
        assert (ws / path).is_file()


@pytest.mark.asyncio
async def test_record_determination_false_skips_file(tmp_path: Path):
    ws = tmp_path / "no_det"
    result = await run_moa_then_team(
        ws,
        "Skip determination artifact?",
        specialist_tasks=[TeamTask("implementer", "apply", "decision.md")],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.8}',
        },
        record_determination=False,
    )
    assert not (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    assert "moa_determination.md" not in result.writes
    assert "decision.md" in result.writes
    # implementer still ok without reading moa_determination.md
    assert result.specialist_results[0].ok is True
    assert "read_file('moa_determination.md')" not in (
        result.specialist_results[0].tool_trace or []
    )


@pytest.mark.asyncio
async def test_soft_panel_failure_skips_specialists_and_determination(tmp_path: Path):
    """When every seat fails (ok_count=0), consensus_then_team must not write or run specialists."""
    ws = tmp_path / "soft_fail"
    result = await run_moa_then_team(
        ws,
        "Should we proceed?",
        specialist_tasks=[
            TeamTask("implementer", "apply", "decision.md"),
            TeamTask("tester", "verify", "test_notes.md"),
        ],
        seed_files={"notes.txt": "seed only"},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        # Non-empty fakes that do not cover seats → all opinions ok=False / ok_count=0.
        moa_fake_responses={"unrelated": "not used by seats"},
        record_determination=True,
    )
    assert result.mode == "consensus_then_team"
    assert result.determination == "No usable participant opinions."
    analysis = (result.moa_payload.get("determination") or {}).get("analysis") or {}
    assert analysis.get("ok_count") == 0
    opinions = result.moa_payload.get("opinions") or []
    assert opinions and all(o.get("ok") is False for o in opinions)
    assert result.specialist_results == []
    assert result.writes == []
    assert result.panel_wrote is False
    # Seed may exist; team must not add determination or specialist artifacts.
    assert (ws / "notes.txt").is_file()
    assert not (ws / "moa_determination.md").exists()
    assert not (ws / "decision.md").exists()
    assert not (ws / "test_notes.md").exists()


@pytest.mark.asyncio
async def test_team_result_to_payload_and_format_consensus_only():
    result = await run_moa_consensus(
        "Rate limit?",
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes with metrics","confidence":0.85}',
        },
    )
    payload = team_result_to_payload(result, question="Rate limit?")
    assert payload["question"] == "Rate limit?"
    assert payload["mode"] == "consensus_only"
    # Same object shape as plain moa --json / run_moa_cli (not a bare string).
    assert isinstance(payload["determination"], dict)
    assert payload["determination"].get("answer")
    assert "answer" in payload["determination"]
    assert "rationale" in payload["determination"]
    assert "participant_names" in payload["determination"]
    assert "analysis" in payload["determination"]
    # Nested moa.determination stays the structured object (aligned top-level).
    assert isinstance((payload.get("moa") or {}).get("determination"), dict)
    assert payload["determination"]["answer"] == (
        payload["moa"]["determination"]["answer"]
    )
    assert payload["specialists"] == []
    assert payload["writes"] == []
    assert payload["reads"] == []
    assert payload["panel_wrote"] is False
    assert isinstance(payload["final_preview"], str)
    assert payload["moa"] is result.moa_payload or payload["moa"].get("opinions")

    text = format_team_text(payload)
    assert "MoA mode: consensus_only" in text
    assert "Question: Rate limit?" in text
    assert "## Determination (orchestrator)" in text
    assert "## Specialists" in text
    assert "consensus only" in text.lower() or "(none" in text
    assert "## Writes" in text
    assert "(none)" in text
    assert "panel_wrote=False" in text
    # No R/W specialist section headers for empty team
    assert "Specialists (R/W team)" not in text


@pytest.mark.asyncio
async def test_team_result_to_payload_and_format_consensus_then_team(tmp_path: Path):
    result = await run_moa_then_team(
        tmp_path / "fmt",
        "Ship?",
        specialist_tasks=[
            TeamTask("implementer", "apply", "decision.md"),
            TeamTask("tester", "verify", "test_notes.md"),
        ],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"ship","confidence":0.9}',
            "critic": '{"claim":"ship","confidence":0.85}',
        },
    )
    payload = team_result_to_payload(result, question="Ship?")
    assert payload["mode"] == "consensus_then_team"
    assert len(payload["specialists"]) == 2
    for s in payload["specialists"]:
        assert "persona" in s and "ok" in s and "output_preview" in s
        assert isinstance(s["output_preview"], str)
        assert s["ok"] is True
    assert "decision.md" in payload["writes"]
    text = format_team_text(payload)
    assert "MoA mode: consensus_then_team" in text
    assert "Specialists (R/W team)" in text
    assert "implementer" in text and "tester" in text
    assert "decision.md" in text


@pytest.mark.asyncio
async def test_researcher_specialist_and_payload(tmp_path: Path):
    result = await run_moa_then_team(
        tmp_path / "r",
        "Map risks?",
        specialist_tasks=parse_team_tasks("researcher:Inventory|implementer:Decide"),
        seed_files={"notes.txt": "edge API"},
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"inventory first","confidence":0.9}',
            "critic": '{"claim":"inventory then decide","confidence":0.85}',
        },
    )
    assert {s.persona for s in result.specialist_results} == {"researcher", "implementer"}
    assert (tmp_path / "r" / "research_notes.md").is_file()
    payload = team_result_to_payload(result, question="Map risks?")
    assert payload["mode"] == "consensus_then_team"
    assert payload["panel_wrote"] is False
    text = format_team_text(payload)
    assert "researcher" in text and "Writes" in text


@pytest.mark.asyncio
async def test_team_emits_info_logs(tmp_path: Path):
    """Champagne INFO trail: key markers present, no secret content leakage.

    Asserts event *tokens* (moa.collect / moa.consult / …) rather than full
    message templates so minor field additions do not break the test.
    """
    records: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    def _has(token: str) -> bool:
        return any(token in m for m in records)

    def _require(*tokens: str) -> None:
        missing = [t for t in tokens if not _has(t)]
        assert not missing, f"missing log token(s) {missing} in: {records!r}"

    handler = _ListHandler(level=logging.INFO)
    loggers = [
        logging.getLogger("swarm.core.moa.team"),
        logging.getLogger("swarm.core.moa.orchestrator"),
    ]
    for log in loggers:
        log.addHandler(handler)
        log.setLevel(logging.INFO)

    secret_q = "SECRET_Q_token_bucket_should_not_appear_in_logs_xyz"
    secret_claim = "SECRET_CLAIM_should_not_appear_in_logs_abc"
    try:
        # --- consensus_only ---
        await run_moa_consensus(
            secret_q,
            moa_backend="fake",
            moa_fake_responses={
                "analyst": f'{{"claim":"{secret_claim}","confidence":0.9}}',
                "critic": f'{{"claim":"{secret_claim}","confidence":0.8}}',
            },
        )
        _require(
            "moa.team consensus_only start",
            "moa.team consensus_only done",
            "moa.run start",
            "moa.run done",
            "moa.collect start",
            "moa.collect done",
            "moa.consult seat=",
            "moa.consult done",
            "moa.determine",
            "permission=approve-reads",
            "act=False",
            "panel_writes=[]",
            "panel_writes_n=0",
        )
        # No soft-OR: collect AND run both fire on the champagne path.
        assert _has("moa.collect") and _has("moa.run start")
        blob = "\n".join(records)
        assert secret_q not in blob
        assert secret_claim not in blob
        # Only lengths of sensitive fields — not bodies.
        assert "q_len=" in blob
        assert "answer_len=" in blob
        assert "text_len=" in blob

        # --- consensus_then_team ---
        records.clear()
        await run_moa_then_team(
            tmp_path / "logws",
            secret_q,
            specialist_tasks=[TeamTask("implementer", "go", "decision.md")],
            moa_backend="fake",
            moa_fake_responses={
                "analyst": f'{{"claim":"{secret_claim}","confidence":0.9}}',
                "critic": f'{{"claim":"{secret_claim}","confidence":0.8}}',
            },
        )
        _require(
            "moa.team consensus_then_team start",
            "moa.team consensus_then_team done",
            "moa.team after_panel",
            "panel_writes_n=0",
            "panel_writes=[]",
            "moa.team wrote moa_determination.md",
            "specialist start purpose=implementer",
            "specialist done purpose=implementer",
            "moa.run start",
            "moa.collect start",
            "moa.determine",
            "permission=approve-reads",
            "act=False",
            "writes_n=",
        )
        blob = "\n".join(records)
        assert secret_q not in blob
        assert secret_claim not in blob
        # Specialist tool traces log paths/ops, not question/claim bodies.
        assert "write_file" in blob
    finally:
        for log in loggers:
            log.removeHandler(handler)


# ---------------------------------------------------------------------------
# Stress tests: parse_team_tasks weird inputs + specialist path / traversal
# ---------------------------------------------------------------------------

_FAKES = {
    "analyst": '{"claim":"yes","confidence":0.9}',
    "critic": '{"claim":"yes","confidence":0.8}',
}


def test_parse_team_tasks_unicode_purpose_and_instruction():
    """Unicode in purpose/instruction is preserved; defaults still apply."""
    tasks = parse_team_tasks(
        "implementer:Apply decision with 日本語 and émojis 🚀|docs:ドキュメントを書く"
    )
    assert tasks is not None
    assert len(tasks) == 2
    assert tasks[0].purpose == "implementer"
    assert "日本語" in tasks[0].instruction
    assert "🚀" in tasks[0].instruction
    assert tasks[0].output_path == "decision.md"
    assert tasks[1].purpose == "docs"
    assert tasks[1].instruction == "ドキュメントを書く"
    assert tasks[1].output_path == "docs/ADR.md"

    # Unicode in purpose alone (no default path for unknown purpose)
    tasks2 = parse_team_tasks("研究:調査する")
    assert tasks2 is not None
    assert tasks2[0].purpose == "研究"
    assert tasks2[0].instruction == "調査する"
    assert tasks2[0].output_path is None


def test_parse_team_tasks_multiple_at_signs():
    """Last @ always splits path; earlier @ stay in the instruction side."""
    tasks = parse_team_tasks("implementer:foo@bar@baz/path.md")
    assert tasks is not None
    assert len(tasks) == 1
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "foo@bar"
    assert tasks[0].output_path == "baz/path.md"

    tasks2 = parse_team_tasks("docs:Write ADR@docs/a@b/ADR.md")
    assert tasks2 is not None
    assert tasks2[0].instruction == "Write ADR@docs/a"
    assert tasks2[0].output_path == "b/ADR.md"

    # Trailing empty @ → default purpose path; instruction keeps head only
    tasks3 = parse_team_tasks("implementer:instr@")
    assert tasks3 is not None
    assert tasks3[0].instruction == "instr"
    assert tasks3[0].output_path == "decision.md"

    tasks4 = parse_team_tasks("tester:@notes.md")
    assert tasks4 is not None
    assert tasks4[0].purpose == "tester"
    assert tasks4[0].instruction == "tester"
    assert tasks4[0].output_path == "notes.md"


def test_parse_team_tasks_spaces_in_purpose_instr_and_path():
    """Whitespace around purpose/instr/path is stripped; internal spaces kept."""
    tasks = parse_team_tasks(
        "  implementer  :  Apply  decision  with spaces  @  out/path with spaces.md  "
    )
    assert tasks is not None
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "Apply  decision  with spaces"
    assert tasks[0].output_path == "out/path with spaces.md"

    tasks2 = parse_team_tasks("docs:Write ADR@docs/my ADR.md")
    assert tasks2 is not None
    assert tasks2[0].output_path == "docs/my ADR.md"
    assert tasks2[0].instruction == "Write ADR"

    tasks3 = parse_team_tasks(
        "  implementer  :  Apply  decision  with spaces  @  out/path.md  "
    )
    assert tasks3 is not None
    assert tasks3[0].purpose == "implementer"
    assert tasks3[0].instruction == "Apply  decision  with spaces"
    assert tasks3[0].output_path == "out/path.md"


def test_parse_team_tasks_empty_instruction_after_colon():
    """Empty / whitespace-only instruction after colon falls back to purpose."""
    for raw in ("implementer:", "implementer:   ", "tester:\t"):
        tasks = parse_team_tasks(raw)
        assert tasks is not None, raw
        assert len(tasks) == 1
        # purpose stripped; instruction becomes purpose when empty
        assert tasks[0].instruction == tasks[0].purpose
        assert tasks[0].output_path is not None  # known purpose defaults


def test_parse_team_tasks_very_long_task_strings():
    """Very long instructions and multi-task pipes parse without error."""
    long_instr = "x" * 50_000
    tasks = parse_team_tasks(f"implementer:{long_instr}@out/long.md")
    assert tasks is not None
    assert len(tasks[0].instruction) == 50_000
    assert tasks[0].output_path == "out/long.md"

    # Many pipe-separated tasks
    parts = [f"implementer:task{i}@out/{i}.md" for i in range(100)]
    tasks2 = parse_team_tasks("|".join(parts))
    assert tasks2 is not None
    assert len(tasks2) == 100
    assert tasks2[0].instruction == "task0"
    assert tasks2[99].output_path == "out/99.md"

    # Long path component (still just a string at parse time)
    long_path = "a/" * 200 + "z.md"
    tasks3 = parse_team_tasks(f"docs:Write@{long_path}")
    assert tasks3 is not None
    assert tasks3[0].output_path == long_path


def test_parse_team_tasks_path_traversal_string_is_preserved():
    """Parser preserves escape paths; WorkspaceTools enforces the boundary later."""
    tasks = parse_team_tasks("implementer:x@../../etc/passwd")
    assert tasks is not None
    assert tasks[0].purpose == "implementer"
    assert tasks[0].instruction == "x"
    assert tasks[0].output_path == "../../etc/passwd"

    tasks2 = parse_team_tasks(
        [{"purpose": "implementer", "instruction": "hi", "output_path": "../../etc/passwd"}]
    )
    assert tasks2 is not None
    assert tasks2[0].output_path == "../../etc/passwd"

    tasks3 = parse_team_tasks(
        [{"purpose": "docs", "instruction": "ADR", "output_path": "/etc/passwd"}]
    )
    assert tasks3 is not None
    assert tasks3[0].output_path == "/etc/passwd"


def test_parse_team_tasks_case_insensitive_default_paths():
    """Default output paths use purpose.lower(); purpose string itself is kept."""
    tasks = parse_team_tasks("IMPLEMENTER:Upper|Tester:Check")
    assert tasks is not None
    assert tasks[0].purpose == "IMPLEMENTER"
    assert tasks[0].output_path == "decision.md"
    assert tasks[1].purpose == "Tester"
    assert tasks[1].output_path == "test_notes.md"


@pytest.mark.asyncio
async def test_specialist_path_traversal_blocked_by_workspace_tools(tmp_path: Path):
    """Parsed or direct escape paths must not write outside workspace.

    parse_team_tasks preserves ``@../../…`` as output_path; WorkspaceTools._safe
    rejects escapes and the specialist fails soft (ok=False).
    """
    ws = tmp_path / "ws"
    evil = tmp_path / "evil"
    evil.mkdir()
    result = await run_moa_then_team(
        ws,
        "pwn?",
        specialist_tasks=parse_team_tasks("implementer:x@../../etc/passwd"),
        moa_backend="fake",
        moa_fake_responses=_FAKES,
    )
    assert len(result.specialist_results) == 1
    s = result.specialist_results[0]
    assert s.ok is False
    assert "escapes workspace" in s.output
    # Legitimate orchestrator artifact may still be written
    assert (ws / "moa_determination.md").is_file()
    assert "../../etc/passwd" not in result.writes
    # Nothing landed outside the workspace root
    assert not any(ws.rglob("passwd"))


@pytest.mark.asyncio
async def test_specialist_sibling_path_escape_blocked(tmp_path: Path):
    """../evil/pwned.md must not write into a sibling of the workspace."""
    ws = tmp_path / "ws_good"
    evil = tmp_path / "ws_evil"
    evil.mkdir()
    result = await run_moa_then_team(
        ws,
        "sibling escape?",
        specialist_tasks=[TeamTask("implementer", "x", "../ws_evil/pwned.md")],
        moa_backend="fake",
        moa_fake_responses=_FAKES,
    )
    assert result.specialist_results[0].ok is False
    assert "escapes workspace" in result.specialist_results[0].output
    assert not (evil / "pwned.md").exists()
    assert "../ws_evil/pwned.md" not in result.writes


@pytest.mark.asyncio
async def test_specialist_absolute_path_escape_blocked(tmp_path: Path):
    result = await run_moa_then_team(
        tmp_path / "ws",
        "abs?",
        specialist_tasks=[TeamTask("docs", "ADR", "/etc/passwd")],
        moa_backend="fake",
        moa_fake_responses=_FAKES,
        record_determination=False,
    )
    assert result.specialist_results[0].ok is False
    assert "escapes workspace" in result.specialist_results[0].output
    assert result.writes == []


@pytest.mark.asyncio
async def test_specialist_safe_relative_path_with_spaces_and_unicode(tmp_path: Path):
    """Weird but in-root paths still write successfully."""
    ws = tmp_path / "ws"
    tasks = parse_team_tasks(
        "implementer:Apply 日本語 decision@out/path with spaces/決.md"
        "|tester:Verify@qa/notes.md"
    )
    result = await run_moa_then_team(
        ws,
        "unicode paths?",
        specialist_tasks=tasks,
        moa_backend="fake",
        moa_fake_responses=_FAKES,
    )
    assert all(s.ok for s in result.specialist_results)
    target = ws / "out" / "path with spaces" / "決.md"
    assert target.is_file()
    body = target.read_text(encoding="utf-8")
    assert "日本語" in body
    assert (ws / "qa" / "notes.md").is_file()


@pytest.mark.asyncio
async def test_specialist_very_long_instruction_writes_ok(tmp_path: Path):
    long_instr = "stress-" + ("y" * 20_000)
    result = await run_moa_then_team(
        tmp_path / "long",
        "long?",
        specialist_tasks=[TeamTask("implementer", long_instr, "decision.md")],
        moa_backend="fake",
        moa_fake_responses=_FAKES,
    )
    assert result.specialist_results[0].ok is True
    body = (tmp_path / "long" / "decision.md").read_text(encoding="utf-8")
    assert long_instr in body


@pytest.mark.asyncio
async def test_mixed_safe_and_escape_paths_partial_success(tmp_path: Path):
    """One escaping specialist fails; later safe specialist still writes."""
    ws = tmp_path / "mix"
    result = await run_moa_then_team(
        ws,
        "mix?",
        specialist_tasks=[
            TeamTask("implementer", "bad", "../../etc/passwd"),
            TeamTask("tester", "good", "test_notes.md"),
        ],
        moa_backend="fake",
        moa_fake_responses=_FAKES,
    )
    by = {s.persona: s for s in result.specialist_results}
    assert by["implementer"].ok is False
    assert by["tester"].ok is True
    assert (ws / "test_notes.md").is_file()
    assert "test_notes.md" in result.writes
    assert "../../etc/passwd" not in result.writes


# ---------------------------------------------------------------------------
# Default fakes ↔ structured schema / determination (demo quality, CI-safe)
# ---------------------------------------------------------------------------


def test_default_fakes_are_valid_structured_json_proposals():
    """Team path defaults emit parseable claim/confidence/evidence JSON."""
    import json

    from swarm.core.moa.schema import parse_proposal
    from swarm.core.moa.team import _default_fakes

    q = 'Ship "feature flags" with canary, or full rollout?'
    fakes = _default_fakes(q)
    assert set(fakes) == {"analyst", "critic"}

    props = []
    for name, raw in fakes.items():
        # Must be real JSON even when the question has quotes / punctuation.
        obj = json.loads(raw)
        assert isinstance(obj, dict)
        assert obj.get("claim")
        assert 0.0 <= float(obj["confidence"]) <= 1.0
        assert isinstance(obj.get("evidence"), list) and obj["evidence"]
        # Question context lives in evidence, not as a truncated claim echo.
        claim = str(obj["claim"])
        assert "Proceed carefully" not in claim
        assert q[:40] not in claim
        assert any(q[:20] in str(e) or "regarding:" in str(e) for e in obj["evidence"])

        prop = parse_proposal(raw)
        assert prop.structured is True, name
        assert prop.confidence is not None
        assert prop.evidence
        props.append(prop)

    # Claims corroborate (shared safer-option language) with slight nuance.
    assert "safer" in props[0].claim.lower()
    assert "safer" in props[1].claim.lower()
    assert props[0].claim != props[1].claim


def test_default_fakes_json_safe_for_adversarial_question_text():
    """Quotes, backslashes, and newlines must not break structured parsing."""
    import json

    from swarm.core.moa.schema import parse_proposal
    from swarm.core.moa.team import _default_fakes

    q = 'Use path C:\\temp\\x and say "yes\\no"?\nSecond line.'
    fakes = _default_fakes(q)
    for raw in fakes.values():
        json.loads(raw)  # raises on invalid JSON
        prop = parse_proposal(raw)
        assert prop.structured is True
        assert prop.claim


def test_default_fakes_score_with_schema_and_synthesize_primary():
    """score_proposals + default_synthesize prefer structured higher-confidence seat."""
    from swarm.core.moa.orchestrator import default_synthesize
    from swarm.core.moa.schema import parse_proposal, score_proposals
    from swarm.core.moa.team import _default_fakes
    from swarm.core.moa.types import ParticipantOpinion

    q = "Should we enable edge rate limiting for the public API?"
    fakes = _default_fakes(q)
    props = [parse_proposal(fakes["analyst"]), parse_proposal(fakes["critic"])]
    ranked = score_proposals(props)
    assert ranked[0][1].structured is True
    # Analyst has higher confidence → ranks first under equal corroboration weight.
    assert ranked[0][1].claim == props[0].claim
    assert ranked[0][0] >= ranked[1][0]

    opinions = [
        ParticipantOpinion(
            name="analyst",
            text=fakes["analyst"],
            ok=True,
            permission_mode="approve-reads",
        ),
        ParticipantOpinion(
            name="critic",
            text=fakes["critic"],
            ok=True,
            permission_mode="approve-reads",
        ),
    ]
    det = default_synthesize(q, opinions)
    assert "safer option" in det.answer.lower()
    assert "rollback" in det.answer.lower()
    assert det.analysis is not None
    assert det.analysis.get("structured_count") == 2
    assert det.analysis.get("primary") == "analyst"
    # Demo quality: not a mid-sentence "Proceed carefully on: <truncated question>"
    assert "Proceed carefully on:" not in det.answer
    assert q[:50] not in det.answer.split("\n")[0]


@pytest.mark.asyncio
async def test_run_moa_consensus_default_fakes_without_explicit_responses():
    """Omitting moa_fake_responses still yields structured determination (CI demo)."""
    q = 'Roll out "caching" with TTL, or skip it?'
    result = await run_moa_consensus(
        q,
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        # intentionally no moa_fake_responses → _default_fakes
    )
    assert result.mode == "consensus_only"
    assert result.writes == []
    assert "safer option" in result.determination.lower()
    assert "rollback" in result.determination.lower() or "monitoring" in result.determination.lower()

    analysis = (result.moa_payload.get("determination") or {}).get("analysis") or {}
    assert analysis.get("structured_count") == 2
    assert analysis.get("primary") == "analyst"

    opinions = result.moa_payload.get("opinions") or []
    assert len(opinions) == 2
    for o in opinions:
        prop = o.get("proposal") or {}
        assert prop.get("structured") is True
        assert prop.get("claim")
        assert prop.get("confidence") is not None
        assert prop.get("evidence")


def test_default_fakes_cover_custom_seat_names():
    """Default fakes follow moa_participants, not only analyst/critic."""
    import json

    from swarm.core.moa.schema import parse_proposal
    from swarm.core.moa.team import _default_fakes

    seats = ["researcher", "skeptic", "ops"]
    fakes = _default_fakes("Ship canary or full rollout?", seats)
    assert set(fakes) == set(seats)
    for name in seats:
        obj = json.loads(fakes[name])
        assert obj.get("claim")
        prop = parse_proposal(fakes[name])
        assert prop.structured is True, name


@pytest.mark.asyncio
async def test_run_moa_consensus_custom_seats_without_explicit_fakes():
    """Custom seats + fake backend must not fail with unknown participant."""
    seats = ["researcher", "skeptic"]
    result = await run_moa_consensus(
        "Prefer canary deploys?",
        moa_backend="fake",
        moa_participants=seats,
        # no moa_fake_responses → _default_fakes(question, seats)
    )
    assert result.mode == "consensus_only"
    opinions = result.moa_payload.get("opinions") or []
    assert len(opinions) == 2
    by_name = {o.get("name"): o for o in opinions}
    assert set(by_name) == set(seats)
    for name in seats:
        o = by_name[name]
        assert o.get("ok") is True, o
        assert not o.get("error"), o
        prop = o.get("proposal") or {}
        assert prop.get("structured") is True
        assert prop.get("claim")


@pytest.mark.asyncio
async def test_run_moa_then_team_default_fakes_feed_specialists(tmp_path: Path):
    """Consensus-then-team without explicit fakes still materializes determination."""
    ws = tmp_path / "def_fakes_team"
    result = await run_moa_then_team(
        ws,
        "Adopt feature flags for risky changes?",
        specialist_tasks=[TeamTask("implementer", "Record decision", "decision.md")],
        moa_backend="fake",
        # no moa_fake_responses
    )
    assert result.mode == "consensus_then_team"
    assert "safer option" in result.determination.lower()
    assert (ws / "moa_determination.md").is_file()
    body = (ws / "moa_determination.md").read_text(encoding="utf-8")
    assert "safer option" in body.lower()
    assert (ws / "decision.md").is_file()
    decision = (ws / "decision.md").read_text(encoding="utf-8")
    assert "safer option" in decision.lower()
    analysis = (result.moa_payload.get("determination") or {}).get("analysis") or {}
    assert analysis.get("structured_count") == 2


# ---------------------------------------------------------------------------
# Team JSON / trace schema — serializer vs docs example assets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_team_payload_accepts_live_serializer(tmp_path: Path):
    """Live team_result_to_payload output passes validate_team_payload."""
    only = await run_moa_consensus(
        "Schema check?",
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.8}',
        },
    )
    only_payload = team_result_to_payload(only, question="Schema check?")
    assert validate_team_payload(only_payload) == []
    assert set(only_payload.keys()) == TEAM_RESULT_PAYLOAD_KEYS

    team = await run_moa_then_team(
        tmp_path / "schema_ws",
        "Schema check?",
        specialist_tasks=[
            TeamTask("implementer", "Apply", "decision.md"),
            TeamTask("tester", "Verify", "test_notes.md"),
        ],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"yes","confidence":0.9}',
            "critic": '{"claim":"yes","confidence":0.8}',
        },
    )
    team_payload = team_result_to_payload(team, question="Schema check?")
    assert validate_team_payload(team_payload) == []
    assert set(team_payload.keys()) == TEAM_RESULT_PAYLOAD_KEYS
    # CLI envelope must be rejected unless allow_cli_envelope
    team_payload["backend"] = "fake"
    issues = validate_team_payload(team_payload)
    assert any("unexpected" in i for i in issues)
    assert validate_team_payload(team_payload, allow_cli_envelope=True) == []


@pytest.mark.parametrize(
    "filename,allow_cli_envelope,expected_mode",
    [
        ("05-demo-consensus-only.json", False, "consensus_only"),
        ("05-demo-consensus-then-team.json", False, "consensus_then_team"),
        ("06-cli-team.json", True, "consensus_then_team"),
    ],
)
def test_example_assets_match_team_result_payload_schema(
    filename: str, allow_cli_envelope: bool, expected_mode: str
):
    """Captured example JSON stays consistent with team_result_to_payload schema.

    * ``05-demo-*.json`` — pure serializer output (demo_moa_consensus_vs_team)
    * ``06-cli-team.json`` — serializer + CLI envelope (backend/participants/…)
    """
    import json

    path = _EXAMPLE_ASSETS / filename
    assert path.is_file(), f"missing example asset {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_team_payload(data, allow_cli_envelope=allow_cli_envelope)
    assert issues == [], f"{filename} schema issues: {issues}"
    assert data["mode"] == expected_mode
    assert data["panel_wrote"] is False
    assert isinstance(data["determination"], dict)
    assert data["determination"].get("answer")
    assert isinstance(data["moa"], dict)
    assert isinstance(data["moa"].get("determination"), dict)
    # Top-level matches nested object shape (plain moa --json compatible).
    assert data["determination"]["answer"] == data["moa"]["determination"]["answer"]
    # Truncation caps from team_result_to_payload
    assert len(data["final_preview"]) <= 800
    for s in data["specialists"]:
        assert len(s["output_preview"]) <= 500
    if allow_cli_envelope:
        # Required CLI envelope fields present on 06-cli-team.json
        for key in ("backend", "participants", "permission", "workdir"):
            assert key in data and data[key], f"{filename} missing CLI envelope {key}"
        assert set(data.keys()) <= (TEAM_RESULT_PAYLOAD_KEYS | TEAM_CLI_ENVELOPE_KEYS)
        # workdir in committed assets must be repo-relative (portable docs)
        assert not str(data["workdir"]).startswith("/"), data["workdir"]
    else:
        assert set(data.keys()) == TEAM_RESULT_PAYLOAD_KEYS


def test_example_contrast_asset_invariants():
    """05-demo-contrast.json is a summary shape (not full team payload).

    Keys use result.mode ids (consensus_only / consensus_then_team), not global
    SWARM_WORKFLOWS Path A/B (where B means openai-agents persona swarm).
    """
    import json

    path = _EXAMPLE_ASSETS / "05-demo-contrast.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {
        "question",
        "consensus_only",
        "consensus_then_team",
        "invariants",
    }
    assert "path_a" not in data and "path_b" not in data
    assert data["consensus_only"]["mode"] == "consensus_only"
    assert data["consensus_only"]["writes"] == []
    assert data["consensus_only"]["panel_wrote"] is False
    assert data["consensus_then_team"]["mode"] == "consensus_then_team"
    assert data["consensus_then_team"]["panel_wrote"] is False
    assert "decision.md" in data["consensus_then_team"]["writes"]
    assert all(data["invariants"].values())
    inv = data["invariants"]
    assert "consensus_only_writes_empty" in inv
    assert "consensus_then_team_has_writes" in inv
    assert "a_writes_empty" not in inv and "b_has_team_writes" not in inv
    # Portable path (no absolute machine path)
    ws = data["consensus_then_team"]["workspace"]
    assert isinstance(ws, str) and not ws.startswith("/")
    assert "demo-team-workspace" in ws


def test_example_readme_does_not_reuse_global_workflow_b_label():
    """moa-consensus-vs-team must not redefine global SWARM_WORKFLOWS Path B.

    Global B is openai-agents persona swarm. This pack is pure MoA (global A)
    and labels its two modes with result.mode ids, never Path A/B.
    """
    readme = (
        _REPO_ROOT / "docs" / "examples" / "moa-consensus-vs-team" / "README.md"
    ).read_text(encoding="utf-8")
    assert "Path B" not in readme
    assert "Path A" not in readme
    assert "consensus_only" in readme
    assert "consensus_then_team" in readme
    assert "No openai-agents required" in readme
    # Anchored under global A (MoA), not global B
    assert "SWARM_WORKFLOWS.md" in readme
    assert "global workflow **A**" in readme
