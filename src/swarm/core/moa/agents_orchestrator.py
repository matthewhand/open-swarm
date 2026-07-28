"""MoA orchestrator in openai-agents mode.

Flow (enforced by construction, not just prompts):

1. **Collect** — read-only MoA participants (fake/grok/acpx) via ``consult_moa``
   (always ``act=False``).
2. **Determine** — local synthesizer (or injectable) owns the consensus text.
3. **Task** — the orchestrator (openai-agents coordinator) may then hand work to
   **specialist R/W agents** (implementer, researcher, tester, …) for purpose-specific
   work. Panelists never receive write tools.

For the same champagne path **without** openai-agents (simple consensus vs
consensus→team), use :mod:`swarm.core.moa.team` —
``run_moa_consensus`` / ``run_moa_then_team``. The scripted body of
``run_moa_agents_orchestrator`` delegates to that runner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm.core.moa.team import (
    SPECIALIST_PURPOSES,
    SpecialistTask,
    TeamTask,
    run_moa_then_team,
)
from swarm.core.moa.tools import consult_moa
from swarm.core.persona_swarm import (
    PersonaResult,
    PersonaSwarmResult,
    WorkspaceTools,
    build_persona_agents,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SPECIALIST_PURPOSES",
    "MoAAgentsOrchestratorResult",
    "SpecialistTask",
    "TeamTask",
    "build_moa_orchestrator_agents",
    "run_moa_agents_orchestrator",
]


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

    def as_persona_result(self) -> PersonaSwarmResult:
        steps = [
            PersonaResult(
                persona="consult_moa",
                instruction="MoA read-only consensus",
                output=self.determination,
                tool_trace=["consult_moa(act=False)"],
                ok=bool(self.determination),
            ),
            *self.specialist_results,
        ]
        return PersonaSwarmResult(
            steps=steps,
            final=self.final or self.determination,
            writes=list(self.writes),
            reads=list(self.reads),
            agents=dict(self.agents),
        )


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
    fakes = moa_fake_responses
    if moa_backend == "fake" and not fakes:
        fakes = {
            "analyst": (
                '{"claim":"Prefer the safer option with clear rollback",'
                '"confidence":0.85}'
            ),
            "critic": (
                '{"claim":"Prefer the safer option and add monitoring",'
                '"confidence":0.8}'
            ),
        }

    moa_calls: list[dict[str, Any]] = agents.get("_moa_calls") or []

    def _consult_configured(question: str) -> str:
        import asyncio
        import concurrent.futures

        async def _run() -> dict[str, Any]:
            return await consult_moa(
                question,
                seats,
                backend=moa_backend,
                fake_responses=fakes,
                cwd=str(tools.root),
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    payload = pool.submit(lambda: asyncio.run(_run())).result()
            else:
                payload = loop.run_until_complete(_run())
        except RuntimeError:
            payload = asyncio.run(_run())

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
) -> MoAAgentsOrchestratorResult:
    """Scripted openai-agents-mode MoA orchestrator (CI-safe).

    Builds the agents roster for inspection / live Runner use, then runs the
    pure :func:`run_moa_then_team` path for deterministic specialist writes.

    Prefer :func:`swarm.core.moa.team.run_moa_then_team` when you do not need
    openai-agents objects at all.
    """
    tools = WorkspaceTools(workspace)
    # Build roster against a throwaway view of the workspace root so agent
    # construction does not pollute write tracking (team runner owns writes).
    agents = build_moa_orchestrator_agents(
        tools,
        moa_backend=moa_backend,
        moa_participants=moa_participants,
        moa_fake_responses=moa_fake_responses,
    )

    team = await run_moa_then_team(
        workspace,
        question,
        specialist_tasks=specialist_tasks,
        seed_files=seed_files,
        moa_backend=moa_backend,
        moa_participants=moa_participants,
        moa_fake_responses=moa_fake_responses,
    )
    return MoAAgentsOrchestratorResult(
        determination=team.determination,
        moa_payload=team.moa_payload,
        specialist_results=list(team.specialist_results),
        writes=list(team.writes),
        reads=list(team.reads),
        agents={
            k: getattr(v, "name", k)
            for k, v in agents.items()
            if not str(k).startswith("_")
        },
        final=team.final,
    )
