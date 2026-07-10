"""MoA orchestrator blueprint — openai-agents mode.

Model id: ``moa_orchestrator``.

1. Collect read-only MoA consensus (``consult_moa``, never act).
2. Task purpose-specific R/W specialists (implementer, tester, docs, researcher)
   based on ``params.tasks`` or a sensible default (implementer only).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.moa.agents_orchestrator import (
    SPECIALIST_PURPOSES,
    SpecialistTask,
    run_moa_agents_orchestrator,
)
from swarm.core.moa.config import resolve_moa_preset

logger = logging.getLogger(__name__)


class MoAOrchestratorBlueprint(BlueprintBase):
    """openai-agents orchestrator: MoA panel then task R/W specialists."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "moa_orchestrator",
        "title": "MoA Agents Orchestrator (consensus then specialists)",
        "description": (
            "Orchestrator runs in openai-agents mode: first collects read-only "
            "MoA consensus (Grok/fake/acpx), then tasks purpose-specific R/W "
            "agents (implementer, tester, docs, researcher). Panelists never write."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["moa", "orchestrator", "openai-agents", "specialists", "hybrid"],
        "aliases": ["moa-orch", "agents_moa"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(
        self,
        blueprint_id: str = "moa_orchestrator",
        config=None,
        config_path=None,
        **kwargs,
    ):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    def _moa_settings(self) -> dict[str, Any]:
        moa_cfg = dict((self._config or {}).get("moa") or {})
        preset = self._params.get("preset")
        if preset:
            try:
                moa_cfg = resolve_moa_preset(moa_cfg, str(preset))
            except KeyError as e:
                logger.warning("%s", e)
        for key in ("backend", "participants", "permission", "fake_responses", "timeout"):
            if key in self._params:
                moa_cfg[key] = self._params[key]
        return moa_cfg

    def _parse_tasks(self) -> list[SpecialistTask] | None:
        raw = self._params.get("tasks")
        if not raw:
            return None
        if isinstance(raw, str):
            # "implementer:do X|tester:check Y"
            tasks = []
            for part in raw.split("|"):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    purpose, instr = part.split(":", 1)
                else:
                    purpose, instr = part, part
                tasks.append(
                    SpecialistTask(purpose=purpose.strip(), instruction=instr.strip())
                )
            return tasks or None
        if isinstance(raw, list):
            tasks = []
            for item in raw:
                if isinstance(item, dict):
                    tasks.append(
                        SpecialistTask(
                            purpose=str(item.get("purpose") or "implementer"),
                            instruction=str(item.get("instruction") or ""),
                            output_path=item.get("output_path"),
                        )
                    )
                elif isinstance(item, str):
                    tasks.append(SpecialistTask(purpose=item, instruction=item))
            return tasks or None
        return None

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        parts = []
        for m in messages or []:
            if isinstance(m, dict) and m.get("content"):
                role = (m.get("role") or "user").upper()
                parts.append(f"{role}: {m['content']}")
        question = "\n\n".join(parts).strip()
        if not question:
            yield {
                "messages": [{"role": "assistant", "content": "No prompt provided."}],
                "final": True,
            }
            return

        settings = self._moa_settings()
        backend = str(settings.get("backend") or "fake")
        participants = settings.get("participants") or ["analyst", "critic"]
        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",") if p.strip()]
        fake = settings.get("fake_responses")
        workdir = self._params.get("workdir") or self._params.get("cwd") or "."
        tasks = self._parse_tasks()

        result = await run_moa_agents_orchestrator(
            workdir,
            question,
            specialist_tasks=tasks,
            seed_files={"notes.txt": question[:2000]},
            moa_backend=backend,
            moa_participants=list(participants),
            moa_fake_responses=dict(fake) if isinstance(fake, dict) else None,
        )

        # Human-readable summary of the full orchestration
        lines = [
            "# MoA Agents Orchestrator",
            "",
            "## Consensus (read-only panel)",
            result.determination or "(empty)",
            "",
            "## Specialist tasks",
        ]
        for s in result.specialist_results:
            status = "ok" if s.ok else "FAIL"
            lines.append(f"### {s.persona} [{status}]")
            lines.append(s.output[:2000] if s.output else "(no output)")
            lines.append("")
        content = "\n".join(lines)
        meta = {
            "moa_orchestrator": True,
            "moa": True,
            "backends": list(participants),
            "specialists": [s.persona for s in result.specialist_results],
            "writes": list(result.writes),
            "specialist_purposes": sorted(SPECIALIST_PURPOSES),
        }
        yield {
            "messages": [{"role": "assistant", "content": content}],
            "role": "assistant",
            "content": content,
            "final": True,
            "meta": meta,
        }
