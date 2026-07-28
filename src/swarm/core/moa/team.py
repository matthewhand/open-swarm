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

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from swarm.core.moa.tools import consult_moa
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


def _default_fakes(question: str) -> dict[str, str]:
    return {
        "analyst": (
            f'{{"claim":"Proceed carefully on: {question[:60]}",'
            f'"confidence":0.85}}'
        ),
        "critic": (
            f'{{"claim":"Proceed carefully and monitor: {question[:60]}",'
            f'"confidence":0.8}}'
        ),
    }


# Default output paths when a task string omits one.
_DEFAULT_OUTPUT_PATHS: dict[str, str] = {
    "implementer": "decision.md",
    "tester": "test_notes.md",
    "docs": "docs/ADR.md",
    "researcher": "research_notes.md",
}


def parse_team_tasks(raw: str | list[Any] | None) -> list[TeamTask] | None:
    """Parse CLI/blueprint task specs into :class:`TeamTask` list.

    String form (pipe-separated)::

        implementer:Apply decision|tester:Verify|docs:ADR@docs/ADR.md

    * ``purpose`` alone → purpose used as instruction; default output path
    * ``purpose:instruction`` → optional instruction
    * ``purpose:instruction@rel/path`` → instruction + explicit output path

    List form accepts dicts ``{purpose, instruction, output_path}`` or strings.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        tasks: list[TeamTask] = []
        for part in raw.split("|"):
            part = part.strip()
            if not part:
                continue
            output_path: str | None = None
            if "@" in part:
                part, output_path = part.rsplit("@", 1)
                output_path = output_path.strip() or None
            if ":" in part:
                purpose, instr = part.split(":", 1)
            else:
                purpose, instr = part, part
            purpose = purpose.strip()
            instr = instr.strip() or purpose
            if output_path is None:
                output_path = _DEFAULT_OUTPUT_PATHS.get(purpose.lower())
            tasks.append(
                TeamTask(
                    purpose=purpose,
                    instruction=instr,
                    output_path=output_path,
                )
            )
        return tasks or None
    if isinstance(raw, list):
        tasks = []
        for item in raw:
            if isinstance(item, TeamTask):
                tasks.append(item)
            elif isinstance(item, dict):
                purpose = str(item.get("purpose") or "implementer")
                tasks.append(
                    TeamTask(
                        purpose=purpose,
                        instruction=str(item.get("instruction") or purpose),
                        output_path=item.get("output_path")
                        or _DEFAULT_OUTPUT_PATHS.get(purpose.lower()),
                    )
                )
            elif isinstance(item, str):
                nested = parse_team_tasks(item)
                if nested:
                    tasks.extend(nested)
        return tasks or None
    return None


def team_result_to_payload(result: MoATeamResult, *, question: str = "") -> dict[str, Any]:
    """Serialize :class:`MoATeamResult` for CLI JSON / traces."""
    return {
        "question": question,
        "mode": result.mode,
        "determination": result.determination,
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


async def run_moa_consensus(
    question: str,
    *,
    moa_backend: str = "fake",
    moa_participants: list[str] | None = None,
    moa_fake_responses: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> MoATeamResult:
    """Simple consensus only: panel opinions + determination, zero team writes.

    Does not construct openai-agents Agents and never schedules specialists.
    """
    seats = list(moa_participants or ["analyst", "critic"])
    fakes = moa_fake_responses
    if moa_backend == "fake" and not fakes:
        fakes = _default_fakes(question)

    logger.info(
        "moa.team consensus_only start backend=%s seats=%s",
        moa_backend,
        seats,
    )
    moa_payload = await consult_moa(
        question,
        seats,
        backend=moa_backend,
        fake_responses=fakes,
        cwd=str(cwd) if cwd is not None else None,
    )
    det = (moa_payload.get("determination") or {}).get("answer") or ""
    panel_writes = list(moa_payload.get("writes") or [])
    logger.info(
        "moa.team consensus_only done answer_len=%d panel_writes=%s specialists=0",
        len(det),
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
    try:
        if purpose == "researcher":
            listing = tools.list_files(".")
            trace.append("list_files('.')")
            notes = ""
            if (tools.root / "notes.txt").exists():
                notes = tools.read_file("notes.txt")
                trace.append("read_file('notes.txt')")
            path = task.output_path or "research_notes.md"
            body = (
                f"# Research\n\n## Task\n{task.instruction}\n\n"
                f"## MoA determination\n{det[:1500]}\n\n"
                f"## Workspace\n{listing}\n\n## Notes\n{notes}\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "implementer":
            path = task.output_path or "decision.md"
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
                f"_Applied by implementer after MoA (scripted team, no openai-agents)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "tester":
            path = task.output_path or "test_notes.md"
            body = (
                f"# Test notes\n\n## Against determination\n{det[:1200]}\n\n"
                f"## Task\n{task.instruction}\n\n"
                f"- [ ] Verify happy path\n- [ ] Verify failure modes\n"
                f"_Tester specialist (R/W, scripted team)._\n"
            )
            tools.write_file(path, body)
            trace.append(f"write_file({path!r})")
            out_parts.append(body)
        elif purpose == "docs":
            path = task.output_path or "docs/ADR.md"
            body = (
                f"# ADR\n\n## Status\nAccepted (post-MoA)\n\n"
                f"## Context\n{question}\n\n## Decision\n{det}\n\n"
                f"## Task\n{task.instruction}\n\n_Docs specialist (R/W, scripted team)._\n"
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
) -> MoATeamResult:
    """Consensus then a scripted R/W team — no openai-agents dependency.

    1. ``consult_moa`` — read-only multi-seat panel + determination (never act)
    2. Optional ``moa_determination.md`` (orchestrator-owned text artifact)
    3. Purpose specialists write files via :class:`WorkspaceTools`
    """
    tools = WorkspaceTools(workspace)
    if seed_files:
        for rel, content in seed_files.items():
            tools.write_file(rel, content)
        tools.writes.clear()
        tools.reads.clear()

    seats = list(moa_participants or ["analyst", "critic"])
    fakes = moa_fake_responses
    if moa_backend == "fake" and not fakes:
        fakes = _default_fakes(question)

    task_names = [t.purpose for t in (specialist_tasks or [])]
    logger.info(
        "moa.team consensus_then_team start backend=%s seats=%s tasks=%s workspace=%s",
        moa_backend,
        seats,
        task_names or ["implementer(default)"],
        tools.root,
    )

    moa_payload = await consult_moa(
        question,
        seats,
        backend=moa_backend,
        fake_responses=fakes,
        cwd=str(tools.root),
    )
    det = (moa_payload.get("determination") or {}).get("answer") or ""
    panel_writes = list(moa_payload.get("writes") or [])
    logger.info(
        "moa.team after_panel answer_len=%d panel_writes=%s (expect [])",
        len(det),
        panel_writes,
    )

    if record_determination:
        tools.write_file(
            "moa_determination.md",
            f"# MoA determination (read-only panel)\n\n{det}\n",
        )
        logger.info("moa.team wrote moa_determination.md (orchestrator-owned)")

    if specialist_tasks is None:
        specialist_tasks = [
            TeamTask(
                purpose="implementer",
                instruction="Apply the MoA determination to decision.md",
                output_path="decision.md",
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
        "moa.team consensus_then_team done specialists_ok=%s writes=%s reads=%s",
        [s.persona for s in specialist_results if s.ok],
        list(tools.writes),
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
