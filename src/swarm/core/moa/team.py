"""MoA without openai-agents: simple consensus vs consensus-then-team.

Two first-class scripted paths (CI-safe, no ``agents`` / Runner dependency):

1. **Consensus only** — read-only multi-seat panel + orchestrator determination.
   No specialist writes.
2. **Consensus then team** — same MoA step, then purpose R/W specialists
   (implementer / tester / docs / researcher) write via :class:`WorkspaceTools`.

The openai-agents orchestrator mode (``run_moa_agents_orchestrator``) reuses the
team runner for its scripted body; live Runner mode is optional and separate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from swarm.core.moa.policy import (
    DEFAULT_PARTICIPANT_PERMISSION,
    WriteDeniedError,
    assert_participant_permission,
)
from swarm.core.moa.tools import consult_moa
from swarm.core.moa.types import PermissionMode
from swarm.core.persona_swarm import PersonaResult, WorkspaceTools

logger = logging.getLogger(__name__)

# Built-in specialist purposes the scripted team runner can schedule.
SPECIALIST_PURPOSES = frozenset(
    {
        "researcher",
        "implementer",
        "tester",
        "docs",
    }
)


@dataclass
class TeamTask:
    """One post-consensus assignment for a R/W specialist (no agents framework)."""

    purpose: str
    instruction: str
    output_path: str | None = None


# Back-compat alias used by openai-agents orchestrator module / blueprints.
SpecialistTask = TeamTask


@dataclass
class MoATeamResult:
    """Outcome of pure MoA consensus or consensus-then-team."""

    determination: str
    moa_payload: dict[str, Any]
    mode: Literal["consensus_only", "consensus_then_team"]
    specialist_results: list[PersonaResult] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    final: str = ""

    @property
    def panel_wrote(self) -> bool:
        """MoA panel never writes; always False for this runner."""
        return False


# Stable key sets for JSON / trace contract checks (tests + capture scripts).
TEAM_RESULT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "question",
        "mode",
        "determination",
        "moa",
        "specialists",
        "writes",
        "reads",
        "panel_wrote",
        "final_preview",
        # Lifted from nested moa for plain ``moa --json`` compatibility
        "opinions",
        "act",
    }
)
SPECIALIST_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "persona",
        "instruction",
        "ok",
        "tool_trace",
        "output_preview",
    }
)
MOA_NESTED_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "question",
        "backend",
        "participants",
        "permission",
        "opinions",
        "determination",
        "writes",
        "act",
    }
)
# Extra keys swarm-cli may attach after team_result_to_payload.
TEAM_CLI_ENVELOPE_KEYS: frozenset[str] = frozenset(
    {
        "backend",
        "participants",
        "permission",
        "workdir",
        "cwd",
        "trace_path",
    }
)


# Rotating claim templates for fake seats (CLI maps texts onto each name the
# same way). Classic analyst/critic keys keep stable wording for demos/tests.
_DEFAULT_FAKE_TEMPLATES: tuple[tuple[str, float, list[str]], ...] = (
    (
        "Prefer the safer option with clear rollback",
        0.85,
        ["clear rollback plan", "minimize blast radius"],
    ),
    (
        "Prefer the safer option and add monitoring",
        0.8,
        ["require monitoring", "expand only after signals"],
    ),
    (
        "Prefer least privilege and deny-by-default for side effects",
        0.78,
        ["least privilege", "deny-by-default"],
    ),
)
_CLASSIC_FAKE_SEATS: dict[str, int] = {"analyst": 0, "critic": 1}


def _default_fakes(
    question: str,
    seats: list[str] | None = None,
) -> dict[str, str]:
    """Structured JSON fake panel opinions for CI / demos (team path).

    Emits ``claim`` / ``confidence`` / ``evidence`` so
    :func:`swarm.core.moa.schema.parse_proposal` marks them structured and
    :func:`swarm.core.moa.orchestrator.default_synthesize` can score them.

    One entry is produced for **each** seat in ``seats`` (default
    ``analyst``/``critic``). Custom ``moa_participants`` must be covered so
    :class:`~swarm.core.moa.backends.FakeParticipantBackend` does not mark
    unknown seats as errors.

    Claims are **stable recommendations** (not a truncated question echo):
    embedding ``question[:N]`` mid-sentence produced awkward determinations,
    and unescaped quotes in the question broke JSON parsing (falling back to
    free-text). The question is attached as evidence context only.
    """
    topic = " ".join((question or "").split())
    if len(topic) > 100:
        topic = topic[:97] + "..."

    names = list(seats) if seats else ["analyst", "critic"]
    out: dict[str, str] = {}
    for i, name in enumerate(names):
        idx = _CLASSIC_FAKE_SEATS.get(name, i % len(_DEFAULT_FAKE_TEMPLATES))
        claim, confidence, evidence_base = _DEFAULT_FAKE_TEMPLATES[idx]
        evidence = list(evidence_base)
        if topic:
            evidence.append(f"regarding: {topic}")
        out[name] = json.dumps(
            {
                "claim": claim,
                "confidence": confidence,
                "evidence": evidence,
            },
            ensure_ascii=False,
        )
    return out


# Default output paths when a task string omits one.
_DEFAULT_OUTPUT_PATHS: dict[str, str] = {
    "implementer": "decision.md",
    "tester": "test_notes.md",
    "docs": "docs/ADR.md",
    "researcher": "research_notes.md",
}

# Recognized artifact extensions for ``purpose:instr@file.ext`` (no slash).
_OUTPUT_PATH_EXTENSIONS: frozenset[str] = frozenset(
    {"md", "txt", "json", "yaml", "yml", "rst", "toml", "csv"}
)


def default_output_path(purpose: str) -> str | None:
    """Return the default relative output path for a specialist purpose.

    Lookup is case-insensitive and strips surrounding whitespace. Unknown
    purposes return ``None``.
    """
    key = (purpose or "").strip().lower()
    if not key:
        return None
    return _DEFAULT_OUTPUT_PATHS.get(key)




def _looks_like_output_path(candidate: str) -> bool:
    """True if *candidate* should be treated as an ``@output_path`` suffix.

    Path-like forms (``out.md``, ``docs/ADR.md``, ``../x.txt``) delimit the
    instruction. Email domains and handles (``example.com``, ``alice``) do not,
    so ``implementer:ping user@example.com`` keeps the full instruction and
    falls back to the purpose default path.
    """
    s = (candidate or "").strip()
    if not s:
        return False
    if "/" in s or "\\" in s:
        return True
    if s.startswith("~") or s.startswith("./") or s.startswith("../"):
        return True
    if "." not in s:
        return False
    ext = s.rsplit(".", 1)[-1].lower()
    return bool(ext) and ext in _OUTPUT_PATH_EXTENSIONS


def _portable_relpath(path: str | None) -> str | None:
    """Normalize workspace-relative paths to POSIX separators (``docs/ADR.md``).

    Keeps CLI/blueprint specs portable across Windows and POSIX hosts. Absolute,
    drive, and ``..`` forms are left intact for :class:`WorkspaceTools` to reject
    at write time.
    """
    if path is None:
        return None
    # Collapse Windows ``\\`` (and accidental doubles) to single POSIX ``/``.
    s = str(path).replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    return s


def _task_from_dict(item: dict[str, Any]) -> TeamTask:
    purpose = str(item.get("purpose") or "implementer").strip() or "implementer"
    instruction = str(item.get("instruction") or purpose).strip() or purpose
    raw_path = item.get("output_path")
    if raw_path is None or (isinstance(raw_path, str) and not str(raw_path).strip()):
        output_path = default_output_path(purpose)
    else:
        output_path = _portable_relpath(str(raw_path).strip())
    return TeamTask(purpose=purpose, instruction=instruction, output_path=output_path)


def _parse_task_segment(part: str) -> TeamTask | None:
    """Parse one ``purpose[:instruction][@path]`` segment.

    Last ``@`` delimits the output path only when the suffix is path-like
    (slash, tilde, or known artifact extension). Empty path after ``@`` falls
    back to the purpose default. Emails/handles stay in the instruction.
    WorkspaceTools rejects escapes at write time.
    """
    part = part.strip()
    if not part:
        return None
    output_path: str | None = None
    if "@" in part:
        left, raw_path = part.rsplit("@", 1)
        raw_path = raw_path.strip()
        if raw_path == "":
            part = left
            output_path = None
        elif _looks_like_output_path(raw_path):
            part = left
            output_path = _portable_relpath(raw_path)
        # else: keep ``@`` in the instruction (email / handle / etc.)
    if ":" in part:
        purpose, instr = part.split(":", 1)
    else:
        purpose, instr = part, part
    purpose = purpose.strip()
    if not purpose:
        return None
    instr = instr.strip() or purpose
    if output_path is None:
        output_path = default_output_path(purpose)
    return TeamTask(purpose=purpose, instruction=instr, output_path=output_path)


def parse_team_tasks(
    raw: str | list[Any] | dict[str, Any] | TeamTask | None,
) -> list[TeamTask] | None:
    """Parse CLI/blueprint task specs into :class:`TeamTask` list.

    String form (pipe-separated)::

        implementer:Apply decision|tester:Verify|docs:ADR@docs/ADR.md

    * ``purpose`` alone -> purpose used as instruction; default output path
    * ``purpose:instruction`` -> optional instruction
    * ``purpose:instruction@rel/path`` -> instruction + explicit output path
      (last ``@`` delimits path; spaces and backslashes preserved as given)

    List form accepts dicts ``{purpose, instruction, output_path}``, strings,
    or :class:`TeamTask` instances. A single dict or :class:`TeamTask` is also
    accepted.

    Return semantics::

    * ``None`` — missing / unspecified (``None`` or ``""``); callers may default
      to implementer.
    * ``[]`` — explicit zero specialists (empty list or pipe-only blanks).
    * non-empty list — parsed specialists.

    Escape rejection is deferred to :class:`WorkspaceTools` at write time.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, TeamTask):
        return [raw]
    if isinstance(raw, dict):
        return [_task_from_dict(raw)]
    if isinstance(raw, str):
        tasks: list[TeamTask] = []
        for part in raw.split("|"):
            task = _parse_task_segment(part)
            if task is not None:
                tasks.append(task)
        return tasks  # may be [] for ||| etc.
    if isinstance(raw, list):
        tasks: list[TeamTask] = []
        for item in raw:
            if isinstance(item, TeamTask):
                if item.output_path and '\\' in item.output_path:
                    item = TeamTask(
                        purpose=item.purpose,
                        instruction=item.instruction,
                        output_path=_portable_relpath(item.output_path),
                    )
                tasks.append(item)
            elif isinstance(item, dict):
                tasks.append(_task_from_dict(item))
            elif isinstance(item, str):
                nested = parse_team_tasks(item)
                if nested:
                    tasks.extend(nested)
                elif nested == []:
                    pass  # explicit empty segment string
        return tasks
    return None



def team_result_to_payload(
    result: MoATeamResult, *, question: str = ""
) -> dict[str, Any]:
    """Serialize :class:`MoATeamResult` for CLI JSON / traces.

    Top-level ``determination`` uses the same object shape as plain
    ``moa --json`` / ``run_moa_cli`` (``answer``, ``rationale``,
    ``participant_names``, ``analysis``) — not a bare string — so scripts can
    always read ``data["determination"]["answer"]`` with or without ``--team``.
    Nested ``moa.determination`` is the same structured form from
    ``consult_moa``.
    """
    moa = result.moa_payload or {}
    nested_det = moa.get("determination")
    if isinstance(nested_det, dict):
        # Same object shape as run_moa_cli (and nested moa.determination).
        determination: dict[str, Any] | None = nested_det
    elif result.determination:
        determination = {
            "answer": result.determination,
            "rationale": "",
            "participant_names": list(moa.get("participants") or []),
            "analysis": None,
        }
    else:
        determination = None
    payload: dict[str, Any] = {
        "question": question,
        "mode": result.mode,
        "determination": determination,
        "moa": result.moa_payload,
        "specialists": [
            {
                "persona": s.persona,
                "instruction": s.instruction,
                "ok": s.ok,
                "tool_trace": list(s.tool_trace),
                "output_preview": (s.output or "")[:500],
            }
            for s in result.specialist_results
        ],
        "writes": list(result.writes),
        "reads": list(result.reads),
        "panel_wrote": result.panel_wrote,
        "final_preview": (result.final or "")[:800],
    }
    # Lift panel fields so plain ``moa --json`` scripts can use top-level
    # ``opinions`` without digging into ``moa`` (same keys as run_moa_cli).
    if isinstance(moa, dict):
        if "opinions" in moa:
            payload["opinions"] = moa.get("opinions")
        if "act" in moa:
            payload["act"] = moa.get("act")
    return payload


def validate_team_payload(
    payload: dict[str, Any], *, allow_cli_envelope: bool = False
) -> list[str]:
    """Return human-readable schema issues for a team JSON / trace payload.

    Used by tests and docs capture checks. When ``allow_cli_envelope`` is true,
    extra keys listed in :data:`TEAM_CLI_ENVELOPE_KEYS` are permitted (CLI
    ``--team --json`` / ``--trace``).
    """
    issues: list[str] = []
    if not isinstance(payload, dict):
        return [f"payload must be a dict, got {type(payload).__name__}"]

    keys = set(payload.keys())
    missing = TEAM_RESULT_PAYLOAD_KEYS - keys
    if missing:
        issues.append(f"missing keys: {sorted(missing)}")
    allowed_extra = TEAM_CLI_ENVELOPE_KEYS if allow_cli_envelope else frozenset()
    extra = keys - TEAM_RESULT_PAYLOAD_KEYS - allowed_extra
    if extra:
        issues.append(f"unexpected keys: {sorted(extra)}")

    if "mode" in payload and payload["mode"] not in (
        "consensus_only",
        "consensus_then_team",
    ):
        issues.append(
            f"mode must be consensus_only|consensus_then_team, got {payload['mode']!r}"
        )

    if "determination" in payload:
        det = payload["determination"]
        if det is not None and not isinstance(det, dict):
            issues.append(
                "top-level determination must be dict|null "
                f"(got {type(det).__name__}); same shape as run_moa_cli / "
                "moa.determination (answer/rationale/participant_names/analysis)"
            )
        elif isinstance(det, dict):
            for req in ("answer", "rationale", "participant_names", "analysis"):
                if req not in det:
                    issues.append(f"top-level determination missing {req!r}")
    if "panel_wrote" in payload and not isinstance(payload["panel_wrote"], bool):
        issues.append("panel_wrote must be bool")
    if "writes" in payload and not isinstance(payload["writes"], list):
        issues.append("writes must be list")
    if "reads" in payload and not isinstance(payload["reads"], list):
        issues.append("reads must be list")
    if "final_preview" in payload and not isinstance(payload["final_preview"], str):
        issues.append("final_preview must be str")
    if "question" in payload and not isinstance(payload["question"], str):
        issues.append("question must be str")

    specs = payload.get("specialists")
    if specs is None:
        issues.append("specialists missing")
    elif not isinstance(specs, list):
        issues.append("specialists must be list")
    else:
        for i, s in enumerate(specs):
            if not isinstance(s, dict):
                issues.append(f"specialists[{i}] must be dict")
                continue
            sk = set(s.keys())
            if sk != SPECIALIST_PAYLOAD_KEYS:
                issues.append(
                    f"specialists[{i}] keys {sorted(sk)} != {sorted(SPECIALIST_PAYLOAD_KEYS)}"
                )
            if "ok" in s and not isinstance(s["ok"], bool):
                issues.append(f"specialists[{i}].ok must be bool")
            if "tool_trace" in s and not isinstance(s["tool_trace"], list):
                issues.append(f"specialists[{i}].tool_trace must be list")
            if "output_preview" in s:
                if not isinstance(s["output_preview"], str):
                    issues.append(f"specialists[{i}].output_preview must be str")
                elif len(s["output_preview"]) > 500:
                    issues.append(
                        f"specialists[{i}].output_preview longer than 500 chars"
                    )
    if "final_preview" in payload and isinstance(payload["final_preview"], str):
        if len(payload["final_preview"]) > 800:
            issues.append("final_preview longer than 800 chars")

    moa = payload.get("moa")
    if moa is None:
        issues.append("moa missing")
    elif not isinstance(moa, dict):
        issues.append("moa must be dict")
    else:
        # Soft check: nested keys should be a subset of known CLI shape.
        unknown = set(moa.keys()) - MOA_NESTED_PAYLOAD_KEYS
        # Allow extra nested keys without failing (forward-compat); only types matter.
        det = moa.get("determination")
        if det is not None and not isinstance(det, dict):
            issues.append("moa.determination must be dict when present")

    return issues


def format_team_text(payload: dict[str, Any]) -> str:
    """Human-readable summary of consensus-only or consensus-then-team."""
    lines: list[str] = []
    mode = payload.get("mode") or "?"
    lines.append(f"MoA mode: {mode}")
    if payload.get("question"):
        lines.append(f"Question: {payload['question']}")
    lines.append("")
    lines.append("## Determination (orchestrator)")
    det = payload.get("determination") or ""
    if isinstance(det, dict):
        det = det.get("answer") or ""
    lines.append((det or "(none)").strip())
    lines.append("")
    specs = payload.get("specialists") or []
    if mode == "consensus_only" or not specs:
        lines.append("## Specialists")
        lines.append("(none — consensus only; no team writes)")
    else:
        lines.append("## Specialists (R/W team)")
        for s in specs:
            status = "ok" if s.get("ok") else "FAIL"
            lines.append(f"### {s.get('persona')} [{status}]")
            if s.get("tool_trace"):
                lines.append(f"trace: {', '.join(s['tool_trace'])}")
            preview = (s.get("output_preview") or "").strip()
            if preview:
                lines.append(preview[:300])
            lines.append("")
    lines.append("## Writes")
    writes = payload.get("writes") or []
    lines.append(", ".join(writes) if writes else "(none)")
    lines.append("")
    lines.append(f"panel_wrote={payload.get('panel_wrote', False)}")
    return "\n".join(lines).rstrip() + "\n"


def _normalize_permission(
    permission: PermissionMode | str | None,
) -> str:
    """Validate participant permission (read-only only)."""
    if permission is None:
        permission = DEFAULT_PARTICIPANT_PERMISSION
    return assert_participant_permission(permission)


async def run_moa_consensus(
    question: str,
    *,
    moa_backend: str = "fake",
    moa_participants: list[str] | None = None,
    moa_fake_responses: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    permission: PermissionMode | str = PermissionMode.APPROVE_READS,
    timeout: float = 300.0,
) -> MoATeamResult:
    """Simple consensus only: panel opinions + determination, zero team writes.

    Does not construct openai-agents Agents and never schedules specialists.
    """
    perm = _normalize_permission(permission)
    seats = list(moa_participants or ["analyst", "critic"])
    fakes = moa_fake_responses
    if moa_backend == "fake" and not fakes:
        fakes = _default_fakes(question, seats)

    logger.info(
        "moa.team consensus_only start backend=%s seats=%s permission=%s",
        moa_backend,
        seats,
        perm,
    )
    moa_payload = await consult_moa(
        question,
        seats,
        backend=moa_backend,
        fake_responses=fakes,
        cwd=str(cwd) if cwd is not None else None,
        permission=perm,
        timeout=timeout,
    )
    det = (moa_payload.get("determination") or {}).get("answer") or ""
    panel_writes = list(moa_payload.get("writes") or [])
    logger.info(
        "moa.team consensus_only done answer_len=%d panel_writes_n=%d panel_writes=%s specialists=0",
        len(det),
        len(panel_writes),
        panel_writes,
    )
    return MoATeamResult(
        determination=det,
        moa_payload=moa_payload,
        mode="consensus_only",
        specialist_results=[],
        writes=[],
        reads=[],
        final=det,
    )


def _run_specialist(
    tools: WorkspaceTools,
    *,
    question: str,
    determination: str,
    task: TeamTask,
) -> PersonaResult:
    purpose = task.purpose.lower().strip()
    if purpose not in SPECIALIST_PURPOSES:
        logger.warning(
            "moa.team specialist unknown purpose=%r",
            task.purpose,
        )
        return PersonaResult(
            persona=task.purpose,
            instruction=task.instruction,
            output=(
                f"unknown specialist purpose {task.purpose!r}; "
                f"known: {sorted(SPECIALIST_PURPOSES)}"
            ),
            ok=False,
        )

    logger.info(
        "moa.team specialist start purpose=%s output_path=%s",
        purpose,
        task.output_path,
    )
    det = determination
    trace: list[str] = []
    out_parts: list[str] = []
    # Known purposes always resolve; empty/None task path falls back to map.
    path = task.output_path or default_output_path(purpose)
    try:
        if purpose == "researcher":
            listing = tools.list_files(".")
            trace.append("list_files('.')")
            notes = ""
            if (tools.root / "notes.txt").exists():
                notes = tools.read_file("notes.txt")
                trace.append("read_file('notes.txt')")
            body = (
                f"# Research\n\n## Task\n{task.instruction}\n\n"
                f"## MoA determination\n{det[:1500]}\n\n"
                f"## Workspace\n{listing}\n\n## Notes\n{notes}\n\n"
                f"_Researcher specialist — scripted team after MoA "
                f"(no openai-agents)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "implementer":
            notes = ""
            if (tools.root / "notes.txt").exists():
                notes = tools.read_file("notes.txt")
                trace.append("read_file('notes.txt')")
            if (tools.root / "moa_determination.md").exists():
                tools.read_file("moa_determination.md")
                trace.append("read_file('moa_determination.md')")
            body = (
                f"# Decision\n\n## Context\n{notes or question}\n\n"
                f"## MoA consensus\n{det}\n\n"
                f"## Task\n{task.instruction}\n\n"
                f"_Implementer specialist — scripted team after MoA "
                f"(no openai-agents)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "tester":
            body = (
                f"# Test notes\n\n## Against determination\n{det[:1200]}\n\n"
                f"## Task\n{task.instruction}\n\n"
                f"- [ ] Verify happy path\n- [ ] Verify failure modes\n\n"
                f"_Tester specialist — scripted team after MoA "
                f"(no openai-agents)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "docs":
            body = (
                f"# ADR\n\n## Status\nAccepted (post-MoA)\n\n"
                f"## Context\n{question}\n\n## Decision\n{det}\n\n"
                f"## Task\n{task.instruction}\n\n"
                f"_Docs specialist — scripted team after MoA "
                f"(no openai-agents)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)

        logger.info(
            "moa.team specialist done purpose=%s ok=True trace=%s",
            purpose,
            trace,
        )
        return PersonaResult(
            persona=purpose,
            instruction=task.instruction,
            output="\n".join(out_parts),
            tool_trace=trace,
            ok=True,
        )
    except Exception as e:
        logger.exception("moa.team specialist failed purpose=%s", purpose)
        return PersonaResult(
            persona=purpose,
            instruction=task.instruction,
            output=str(e),
            tool_trace=trace,
            ok=False,
        )



def _moa_panel_usable(moa_payload: dict[str, Any]) -> bool:
    """Return True if the consult_moa payload has at least one usable opinion.

    Soft panel failures synthesize a degradation determination with
    ``analysis.ok_count == 0`` (and typically every ``opinions[].ok`` is False).
    Team path must not schedule R/W specialists or write determination artifacts
    when the panel produced nothing usable.
    """
    det = moa_payload.get("determination") or {}
    if isinstance(det, dict):
        analysis = det.get("analysis") or {}
        if isinstance(analysis, dict) and "ok_count" in analysis:
            try:
                return int(analysis.get("ok_count") or 0) > 0
            except (TypeError, ValueError):
                pass
    opinions = moa_payload.get("opinions") or []
    if not opinions:
        return False
    return any(
        isinstance(o, dict) and bool(o.get("ok")) for o in opinions
    )


def team_cli_failed(result: MoATeamResult) -> bool:
    """Return True when ``swarm-cli moa --team`` should exit non-zero.

    Soft failures: unusable panel (ok_count=0 / no ok opinions) or any
    specialist with ``ok=False``. Callers still print the payload, then exit 1.
    """
    if not _moa_panel_usable(result.moa_payload):
        return True
    return any(not s.ok for s in result.specialist_results)


async def run_moa_then_team(
    workspace: str | Path,
    question: str,
    *,
    specialist_tasks: list[TeamTask] | None = None,
    seed_files: dict[str, str] | None = None,
    moa_backend: str = "fake",
    moa_participants: list[str] | None = None,
    moa_fake_responses: dict[str, str] | None = None,
    record_determination: bool = True,
    permission: PermissionMode | str = PermissionMode.APPROVE_READS,
    cwd: str | Path | None = None,
    timeout: float = 300.0,
) -> MoATeamResult:
    """Consensus then a scripted R/W team — no openai-agents dependency.

    1. ``consult_moa`` — read-only multi-seat panel + determination (never act)
    2. Optional ``moa_determination.md`` (orchestrator-owned text artifact)
    3. Purpose specialists write files via :class:`WorkspaceTools`

    Participant ``permission`` must be a read-only mode (``approve-reads`` /
    ``deny-all``). Specialists still write; only panelists are permission-locked.
    Path escapes in ``TeamTask.output_path`` are rejected by WorkspaceTools.
    """
    perm = _normalize_permission(permission)
    tools = WorkspaceTools(workspace)
    if seed_files:
        # Seed = create-if-missing; never overwrite existing workspace context
        # (e.g. a user-authored notes.txt under --workdir).
        for rel, content in seed_files.items():
            dest = tools._safe(rel)
            if not dest.exists():
                tools.write_file(rel, content)
        tools.writes.clear()
        tools.reads.clear()

    seats = list(moa_participants or ["analyst", "critic"])
    fakes = moa_fake_responses
    if moa_backend == "fake" and not fakes:
        fakes = _default_fakes(question, seats)

    panel_cwd = str(cwd) if cwd is not None else str(tools.root)

    if specialist_tasks is None:
        log_tasks = ["implementer(default)"]
    else:
        log_tasks = [t.purpose for t in specialist_tasks] or ["(none)"]
    logger.info(
        "moa.team consensus_then_team start backend=%s seats=%s tasks=%s "
        "permission=%s workspace=%s",
        moa_backend,
        seats,
        log_tasks,
        perm,
        tools.root,
    )

    moa_payload = await consult_moa(
        question,
        seats,
        backend=moa_backend,
        fake_responses=fakes,
        cwd=panel_cwd,
        permission=perm,
        timeout=timeout,
    )
    det = (moa_payload.get("determination") or {}).get("answer") or ""
    panel_writes = list(moa_payload.get("writes") or [])
    logger.info(
        "moa.team after_panel answer_len=%d panel_writes_n=%d panel_writes=%s (expect [])",
        len(det),
        len(panel_writes),
        panel_writes,
    )

    # Soft panel failure: do not write moa_determination.md or schedule specialists.
    if not _moa_panel_usable(moa_payload):
        logger.warning(
            "moa.team panel unusable (ok_count=0 / no ok opinions); "
            "skipping determination artifact and specialists"
        )
        return MoATeamResult(
            determination=det,
            moa_payload=moa_payload,
            mode="consensus_then_team",
            specialist_results=[],
            writes=[],
            reads=list(tools.reads),
            final=det,
        )

    if record_determination:
        tools.write_file(
            "moa_determination.md",
            f"# MoA determination (read-only panel)\n\n{det}\n",
        )
        logger.info("moa.team wrote moa_determination.md (orchestrator-owned)")

    # None = missing tasks → default implementer.
    # [] = explicitly zero specialists (do not alias to the default).
    if specialist_tasks is None:
        impl_path = default_output_path("implementer")
        specialist_tasks = [
            TeamTask(
                purpose="implementer",
                instruction=f"Apply the MoA determination to {impl_path}",
                output_path=impl_path,
            ),
        ]

    specialist_results: list[PersonaResult] = []
    for task in specialist_tasks:
        specialist_results.append(
            _run_specialist(
                tools,
                question=question,
                determination=det,
                task=task,
            )
        )

    final = specialist_results[-1].output if specialist_results else det
    logger.info(
        "moa.team consensus_then_team done specialists_ok=%s writes_n=%d writes=%s reads_n=%d reads=%s",
        [s.persona for s in specialist_results if s.ok],
        len(tools.writes),
        list(tools.writes),
        len(tools.reads),
        list(tools.reads),
    )
    return MoATeamResult(
        determination=det,
        moa_payload=moa_payload,
        mode="consensus_then_team",
        specialist_results=specialist_results,
        writes=list(tools.writes),
        reads=list(tools.reads),
        final=final,
    )


# Re-export for type checkers / callers that expect policy error nearby.
__all__ = [
    "MOA_NESTED_PAYLOAD_KEYS",
    "MoATeamResult",
    "SPECIALIST_PAYLOAD_KEYS",
    "SPECIALIST_PURPOSES",
    "SpecialistTask",
    "TEAM_CLI_ENVELOPE_KEYS",
    "TEAM_RESULT_PAYLOAD_KEYS",
    "TeamTask",
    "WriteDeniedError",
    "format_team_text",
    "default_output_path",
    "parse_team_tasks",
    "run_moa_consensus",
    "run_moa_then_team",
    "team_cli_failed",
    "team_result_to_payload",
    "validate_team_payload",
]
