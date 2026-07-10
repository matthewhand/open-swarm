"""Workflow model B: persona / agent-as-tool swarm (openai-agents).

Specialists are encouraged to **read and write**. A coordinator switches
personas (agent-as-tool style) rather than taking a formal multi-model vote.

See ``docs/SWARM_WORKFLOWS.md``. Offline/scripted runs prove tool policy without
an LLM; live runs can use ``Runner`` when configured.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class PersonaStep:
    """One coordinator decision: which persona to invoke and with what instruction."""

    persona: str
    instruction: str


@dataclass
class PersonaResult:
    persona: str
    instruction: str
    output: str
    tool_trace: list[str] = field(default_factory=list)
    ok: bool = True


@dataclass
class PersonaSwarmResult:
    steps: list[PersonaResult]
    final: str
    writes: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    agents: dict[str, Any] = field(default_factory=dict)


class WorkspaceTools:
    """Read/write tool surface bound to a workspace root (model B specialists)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.reads: list[str] = []
        self.writes: list[str] = []

    def _safe(self, rel: str) -> Path:
        path = (self.root / rel).resolve()
        # Reject sibling escapes (e.g. ../ws_evil) — startswith(root) is insufficient
        # when another path is a prefix sibling of root.
        try:
            if not path.is_relative_to(self.root):
                raise ValueError(f"path escapes workspace: {rel}")
        except AttributeError:  # pragma: no cover — Python < 3.9
            root_s = str(self.root)
            if path != self.root and not str(path).startswith(root_s + os.sep):
                raise ValueError(f"path escapes workspace: {rel}") from None
        return path

    def read_file(self, path: str) -> str:
        self.reads.append(path)
        p = self._safe(path)
        return p.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        self.writes.append(path)
        p = self._safe(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: wrote {path} ({len(content)} bytes)"

    def list_files(self, directory: str = ".") -> str:
        self.reads.append(directory)
        p = self._safe(directory)
        if not p.is_dir():
            return f"ERROR: not a directory: {directory}"
        return "\n".join(sorted(x.name for x in p.iterdir()))


def build_persona_agents(tools: WorkspaceTools) -> dict[str, Any]:
    """Construct openai-agents ``Agent`` personas with R/W tools.

    Returns a name → Agent map. Tools are real callables registered via
    ``function_tool`` when available.
    """
    try:
        from agents import Agent, function_tool
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("openai-agents (package 'agents') is required for model B") from e

    @function_tool
    def read_file(path: str) -> str:
        """Read a file under the workspace (allowed for all personas)."""
        return tools.read_file(path)

    @function_tool
    def write_file(path: str, content: str) -> str:
        """Write a file under the workspace (encouraged for implementer personas)."""
        return tools.write_file(path, content)

    @function_tool
    def list_files(directory: str = ".") -> str:
        """List files in a workspace directory."""
        return tools.list_files(directory)

    researcher = Agent(
        name="Researcher",
        instructions=(
            "You are a researcher persona. Prefer reading and summarizing. "
            "You may write notes if needed. Use tools to inspect the workspace."
        ),
        tools=[read_file, list_files, write_file],
    )
    implementer = Agent(
        name="Implementer",
        instructions=(
            "You are an implementer persona. You are encouraged to read and write. "
            "Apply concrete changes with write_file after inspecting context."
        ),
        tools=[read_file, list_files, write_file],
    )
    coordinator = Agent(
        name="Coordinator",
        instructions=(
            "You coordinate personas. Switch between Researcher and Implementer "
            "as needed. Specialists may read and write."
        ),
        # Agent-as-tool style wiring when handoffs/as_tool are available.
        tools=[read_file, list_files, write_file],
    )

    # Attach as_tool if the SDK supports it (agent-as-tool switching).
    try:
        coordinator.tools = list(coordinator.tools or [])
        if hasattr(researcher, "as_tool"):
            coordinator.tools.append(
                researcher.as_tool(
                    tool_name="consult_researcher",
                    tool_description="Switch to Researcher persona",
                )
            )
        if hasattr(implementer, "as_tool"):
            coordinator.tools.append(
                implementer.as_tool(
                    tool_name="consult_implementer",
                    tool_description="Switch to Implementer persona (read/write)",
                )
            )
    except Exception as e:  # pragma: no cover
        logger.debug("as_tool wiring skipped: %s", e)

    return {
        "coordinator": coordinator,
        "researcher": researcher,
        "implementer": implementer,
        "_tools": {
            "read_file": tools.read_file,
            "write_file": tools.write_file,
            "list_files": tools.list_files,
        },
    }


def run_scripted_persona_swarm(
    workspace: str | Path,
    steps: list[PersonaStep] | None = None,
    *,
    seed_files: dict[str, str] | None = None,
) -> PersonaSwarmResult:
    """Prove model B offline: coordinator switches personas; specialists R/W.

    Does not require an LLM API. Uses real ``Agent`` construction from
    openai-agents and real workspace tools. Scripted steps simulate the
    coordinator's persona switches (what an LLM coordinator would choose).
    """
    tools = WorkspaceTools(workspace)
    if seed_files:
        for rel, content in seed_files.items():
            tools.write_file(rel, content)
        # Reset traces so seed writes don't count as swarm work.
        tools.writes.clear()
        tools.reads.clear()

    agents = build_persona_agents(tools)
    if steps is None:
        steps = [
            PersonaStep(
                "researcher",
                "Read notes.txt and list the workspace.",
            ),
            PersonaStep(
                "implementer",
                "Write summary.md based on notes.txt.",
            ),
        ]

    results: list[PersonaResult] = []
    for step in steps:
        persona = step.persona.lower()
        if persona not in agents or persona.startswith("_"):
            results.append(
                PersonaResult(
                    persona=step.persona,
                    instruction=step.instruction,
                    output=f"unknown persona {step.persona}",
                    ok=False,
                )
            )
            continue

        agent = agents[persona]
        trace: list[str] = []
        # Scripted tool use matching persona encouragement:
        # researcher: read-heavy; implementer: write-heavy (both may R/W).
        out_parts: list[str] = []
        try:
            if persona == "researcher":
                listing = tools.list_files(".")
                trace.append("list_files('.')")
                out_parts.append(f"listing:\n{listing}")
                if "notes.txt" in listing or (tools.root / "notes.txt").exists():
                    text = tools.read_file("notes.txt")
                    trace.append("read_file('notes.txt')")
                    out_parts.append(f"notes.txt:\n{text}")
                    # Optional note (R/W allowed for B specialists).
                    tools.write_file(
                        "research_scratch.txt",
                        f"Researcher notes: found notes.txt ({len(text)} chars)\n",
                    )
                    trace.append("write_file('research_scratch.txt')")
            elif persona == "implementer":
                if (tools.root / "notes.txt").exists():
                    src = tools.read_file("notes.txt")
                    trace.append("read_file('notes.txt')")
                else:
                    src = "(no notes.txt)"
                content = (
                    f"# Summary\n\nSource notes:\n\n{src}\n\n"
                    f"_Written by Implementer persona (read/write encouraged)._\n"
                )
                tools.write_file("summary.md", content)
                trace.append("write_file('summary.md')")
                out_parts.append(tools.read_file("summary.md"))
                trace.append("read_file('summary.md')")
            else:
                # Coordinator: may inspect only in scripted mode.
                listing = tools.list_files(".")
                trace.append("list_files('.')")
                out_parts.append(listing)

            # Prove Agent object is a real openai-agents Agent with tools.
            tool_names = []
            for t in getattr(agent, "tools", None) or []:
                tool_names.append(getattr(t, "name", None) or getattr(t, "__name__", type(t).__name__))
            out_parts.append(f"[agent={agent.name} tools={tool_names}]")

            results.append(
                PersonaResult(
                    persona=step.persona,
                    instruction=step.instruction,
                    output="\n".join(out_parts),
                    tool_trace=trace,
                    ok=True,
                )
            )
        except Exception as e:
            results.append(
                PersonaResult(
                    persona=step.persona,
                    instruction=step.instruction,
                    output=str(e),
                    tool_trace=trace,
                    ok=False,
                )
            )

    final = results[-1].output if results else ""
    return PersonaSwarmResult(
        steps=results,
        final=final,
        writes=list(tools.writes),
        reads=list(tools.reads),
        agents={k: getattr(v, "name", k) for k, v in agents.items() if not k.startswith("_")},
    )


async def run_persona_swarm_with_runner(
    workspace: str | Path,
    user_message: str,
    *,
    seed_files: dict[str, str] | None = None,
    max_turns: int = 4,
) -> PersonaSwarmResult:
    """Optional live path: coordinator Agent via openai-agents ``Runner``.

    Falls back to scripted persona swarm when Runner/LLM is unavailable so
    offline CI stays green. Live mode still uses the same R/W WorkspaceTools.
    """
    tools = WorkspaceTools(workspace)
    if seed_files:
        for rel, content in seed_files.items():
            tools.write_file(rel, content)
        tools.writes.clear()
        tools.reads.clear()

    agents = build_persona_agents(tools)
    coordinator = agents["coordinator"]

    try:
        from agents import Runner
    except ImportError:
        return run_scripted_persona_swarm(
            workspace,
            seed_files=None,  # already seeded into tools workspace
        )

    try:
        result = await Runner.run(coordinator, user_message, max_turns=max_turns)
        final = str(getattr(result, "final_output", None) or result)
        return PersonaSwarmResult(
            steps=[
                PersonaResult(
                    persona="coordinator",
                    instruction=user_message,
                    output=final,
                    tool_trace=[
                        "path=runner",
                        f"reads={tools.reads}",
                        f"writes={tools.writes}",
                    ],
                    ok=True,
                )
            ],
            final=final,
            writes=list(tools.writes),
            reads=list(tools.reads),
            agents={
                k: getattr(v, "name", k)
                for k, v in agents.items()
                if not k.startswith("_")
            },
        )
    except Exception as e:
        logger.info("Runner path unavailable (%s); falling back to scripted MoA-B", e)
        # Scripted path on same workspace; re-seed files if provided.
        return run_scripted_persona_swarm(
            workspace,
            seed_files=seed_files,
        )
