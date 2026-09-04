"""MoA orchestrator surface (agents-shaped API; scripted by default).

Default dogfood / CI path (:func:`run_moa_agents_orchestrator`):

1. **Collect** — read-only MoA participants (fake/grok/acpx) via ``consult_moa``
   (no ``act`` parameter; always no-act).
2. **Determine** — local synthesizer owns the consensus text.
3. **Task** — scripted purpose specialists (implementer / tester / docs /
   researcher) via :func:`swarm.core.moa.team.run_moa_then_team` +
   ``WorkspaceTools``. Panelists never write.

This is **not** a live openai-agents ``Runner`` path. Optional live Agent
construction is :func:`build_moa_orchestrator_agents` only.

For the pure team API without the agents-shaped result wrapper, use
:mod:`swarm.core.moa.team` directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm.core.async_utils import run_coro_sync
from swarm.core.moa.policy import DEFAULT_PARTICIPANT_PERMISSION
from swarm.core.moa.team import (
    SPECIALIST_PURPOSES,
    SpecialistTask,
    _default_fakes,
    run_moa_then_team,
)
from swarm.core.moa.tools import consult_moa
from swarm.core.moa.types import PermissionMode
from swarm.core.persona_swarm import (
    PersonaResult,
    WorkspaceTools,
    build_persona_agents,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SPECIALIST_PURPOSES",
    "SCRIPTED_ORCHESTRATOR_ROSTER",
    "MoAAgentsOrchestratorResult",
    "SpecialistTask",
    "build_moa_orchestrator_agents",
    "run_moa_agents_orchestrator",
]

# Display-name roster for the scripted orchestrator path. Matches the keys/names
# produced by :func:`build_moa_orchestrator_agents` without constructing Agents.
# Building real openai-agents objects costs hundreds of ms and is unused by the
# deterministic team runner that actually executes specialist writes.
SCRIPTED_ORCHESTRATOR_ROSTER: dict[str, str] = {
    "coordinator": "Coordinator",
    "researcher": "Researcher",
    "implementer": "Implementer",
    "tester": "Tester",
    "docs": "Docs",
}


@dataclass
class MoAAgentsOrchestratorResult:
    """Outcome of openai-agents-mode MoA orchestration."""

    determination: str
    moa_payload: dict[str, Any]
    specialist_results: list[PersonaResult] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    agents: dict[str, Any] = field(default_factory=dict)
    final: str = ""


def build_moa_orchestrator_agents(
    tools: WorkspaceTools,
    *,
    moa_backend: str = "fake",
    moa_participants: list[str] | None = None,
    moa_fake_responses: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build openai-agents roster: coordinator + R/W specialists + MoA tool.

    The coordinator is the **orchestrator in agents mode**: it can call
    ``consult_moa_panel`` (read-only) and specialist tools (R/W).
    """
    # Reuse persona agent construction (includes consult_moa_panel on coordinator).
    agents = build_persona_agents(tools)

    # Override MoA consult defaults to caller's backend/participants when possible.
    seats = list(moa_participants or ["analyst", "critic"])
    fakes_override = moa_fake_responses

    moa_calls: list[dict[str, Any]] = agents.get("_moa_calls") or []

    def _consult_configured(question: str) -> str:
        import asyncio
        import concurrent.futures

        # Match scripted run_moa_then_team / run_moa_agents_orchestrator defaults.
        fakes = fakes_override
        if moa_backend == "fake" and not fakes:
            fakes = _default_fakes(question, seats)

        async def _run() -> dict[str, Any]:
            return await consult_moa(
                question,
                seats,
                backend=moa_backend,
                fake_responses=fakes,
                cwd=str(tools.root),
            )

        payload = run_coro_sync(_run())

        moa_calls.append({"question": question, "payload": payload})
        det = (payload or {}).get("determination") or {}
        answer = det.get("answer") or "(no determination)"
        return f"[MoA determination — read-only panel]\n{answer}"

    # Replace consult_moa helper with configured backend.
    agents["_tools"]["consult_moa"] = _consult_configured
    agents["_moa_calls"] = moa_calls
    agents["_moa_config"] = {
        "backend": moa_backend,
        "participants": seats,
    }

    # Live path: coordinator still has persona_swarm's consult_moa_panel which
    # hardcodes backend="fake". Rebuild the tool so Runner uses configured MoA.
    try:
        from agents import function_tool as _function_tool

        @_function_tool
        def consult_moa_panel(question: str) -> str:
            """Call Mixture of Agents for a read-only multi-seat consensus opinion.

            Use before high-stakes writes. Participants cannot write; you (or the
            implementer) apply changes after reviewing the determination.
            """
            return _consult_configured(question)

        coord = agents["coordinator"]
        kept = [
            t
            for t in list(coord.tools or [])
            if getattr(t, "name", None) != "consult_moa_panel"
        ]
        coord.tools = kept + [consult_moa_panel]
    except Exception as e:  # pragma: no cover
        logger.debug("consult_moa_panel rewire skipped: %s", e)

    # Extra specialist: tester + docs as lightweight R/W roles (same tool surface).
    try:
        from agents import Agent, function_tool

        @function_tool
        def read_file(path: str) -> str:
            return tools.read_file(path)

        @function_tool
        def write_file(path: str, content: str) -> str:
            return tools.write_file(path, content)

        @function_tool
        def list_files(directory: str = ".") -> str:
            return tools.list_files(directory)

        tester = Agent(
            name="Tester",
            instructions=(
                "You are a tester persona. After MoA consensus, verify claims: "
                "inspect the workspace, write test notes, and flag risks. You may "
                "read and write verification artifacts."
            ),
            tools=[read_file, list_files, write_file],
        )
        docs = Agent(
            name="Docs",
            instructions=(
                "You are a documentation persona. After MoA consensus, write clear "
                "docs/ADRs based on the determination. You may read and write docs."
            ),
            tools=[read_file, list_files, write_file],
        )
        agents["tester"] = tester
        agents["docs"] = docs

        coord = agents["coordinator"]
        coord.instructions = (
            "You are the MoA orchestrator in openai-agents mode. "
            "1) Always call consult_moa_panel (or consult_moa) first for high-stakes "
            "decisions — that panel is READ-ONLY. "
            "2) After you have a determination, task purpose-specific agents: "
            "Researcher (inspect), Implementer (code/config changes), Tester "
            "(verification notes), Docs (documentation). "
            "3) Never assume the MoA panel wrote files; only specialists write."
        )
        # Attach specialist as_tool when available
        try:
            coord.tools = list(coord.tools or [])
            for name, agent, desc in (
                ("tester", tester, "Tester persona — verify and write test notes"),
                ("docs", docs, "Docs persona — write documentation from consensus"),
            ):
                if hasattr(agent, "as_tool"):
                    coord.tools.append(
                        agent.as_tool(tool_name=f"task_{name}", tool_description=desc)
                    )
        except Exception as e:  # pragma: no cover
            logger.debug("specialist as_tool wiring skipped: %s", e)
    except Exception as e:  # pragma: no cover
        logger.debug("extra specialists skipped: %s", e)

    return agents


async def run_moa_agents_orchestrator(
    workspace: str | Path,
    question: str,
    *,
    specialist_tasks: list[SpecialistTask] | None = None,
    seed_files: dict[str, str] | None = None,
    moa_backend: str = "fake",
    moa_participants: list[str] | None = None,
    moa_fake_responses: dict[str, str] | None = None,
    record_determination: bool = True,
    permission: PermissionMode | str = DEFAULT_PARTICIPANT_PERMISSION,
    cwd: str | Path | None = None,
    timeout: float = 300.0,
) -> MoAAgentsOrchestratorResult:
    """Scripted openai-agents-mode MoA orchestrator (CI-safe).

    Thin wrapper around :func:`run_moa_then_team` for deterministic specialist
    writes. Shared kwargs (``permission`` / ``cwd`` / ``timeout`` /
    ``record_determination``) are forwarded so both entrypoints stay at parity.

    ``result.agents`` is a lightweight name roster for inspection (same
    keys/display names as :func:`build_moa_orchestrator_agents`). Real
    openai-agents objects are **not** constructed here — call
    :func:`build_moa_orchestrator_agents` when you need live Runner wiring.

    Prefer :func:`swarm.core.moa.team.run_moa_then_team` when you do not need
    the agents-mode result shape at all.
    """
    team = await run_moa_then_team(
        workspace,
        question,
        specialist_tasks=specialist_tasks,
        seed_files=seed_files,
        moa_backend=moa_backend,
        moa_participants=moa_participants,
        moa_fake_responses=moa_fake_responses,
        record_determination=record_determination,
        permission=permission,
        cwd=cwd,
        timeout=timeout,
    )
    return MoAAgentsOrchestratorResult(
        determination=team.determination,
        moa_payload=team.moa_payload,
        specialist_results=list(team.specialist_results),
        writes=list(team.writes),
        reads=list(team.reads),
        agents=dict(SCRIPTED_ORCHESTRATOR_ROSTER),
        final=team.final,
    )
