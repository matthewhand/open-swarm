"""Hybrid team blueprint: a REST reasoning step MIXED with CLI agents.

A small "team" that mixes backends in a single ``run()``:

  * a REST-style LLM reasoning step (the *coordinator*; deterministic under
    ``SWARM_TEST_MODE``),
  * a grok CLI *persona*        (:func:`swarm.core.cli_tools.cli_persona` over a
    :class:`~swarm.core.cli_adapter.CliAdapter`),
  * a cross-model *consensus*   (:func:`swarm.core.cli_tools.consensus_fn` /
    :func:`swarm.core.consensus.run_consensus`).

The REST coordinator holds the master plan and delegates sub-questions to the
grok/claude CLI personas (exposed as ``cli_tools`` callables) and to a consensus
panel — that is the MIX: one REST inference reaching for CLI personas mid-run.

Deterministic in tests two ways, independently:

  * REST half -> stubbed when ``os.environ["SWARM_TEST_MODE"]`` is set.
  * CLI half  -> driven by a configured ``cli_agents`` block of fake echo CLIs
                 (``python -c '... print(...)'``; see
                 ``tests/blueprints/test_hybrid_team.py``), so no model/network.

Request model: ``model: "hybrid_team"``. Config block ``hybrid_team``::

    {"grok": "<cli-name>", "panel": ["<cli>", ...], "judge": "<cli>"}

falls back to the ``cli_fusion`` ``default_cli`` / ``default_preset``. Per-request
``params`` may override ``grok`` / ``panel`` / ``judge`` / ``workdir`` / ``timeout``.
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.cli_adapter import CliAdapterRegistry
from swarm.core.cli_tools import cli_persona, consensus_fn  # the granular tool layer
from swarm.core.consensus import run_consensus  # noqa: F401  (Option B; see run())


class HybridTeamBlueprint(BlueprintBase):
    """REST coordinator + grok CLI persona + consensus panel, in one run()."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "hybrid_team",
        "title": "Hybrid Team (REST coordinator + CLI agents)",
        "description": (
            "A REST coordinator that reasons, then delegates to a grok CLI "
            "persona and a cross-model consensus panel — backends mixed in a "
            "single request."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "fusion", "rest", "consensus", "hybrid", "openai-compatible"],
        # The coordinator reasons and plans, so it asks for high intelligence;
        # speed/cost are "don't care". Scored against swarm_config.json `llm`
        # profiles (see core/inference_profile.py). A hint only — explicit
        # llm_profile / DEFAULT_LLM / LITELLM_MODEL still take priority.
        "inference_profile": {"intelligence": 0.9},
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(
        self,
        blueprint_id: str = "hybrid_team",
        config=None,
        config_path=None,
        **kwargs,
    ):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    # --- config resolution: grok persona + consensus panel ---------------- #

    def _resolve(
        self, params: dict[str, Any], registry: CliAdapterRegistry
    ) -> tuple[str | None, list[str], str | None]:
        """Resolve (grok_cli, panel, judge), falling back to cli_fusion config."""
        hc = (self._config or {}).get("hybrid_team") or {}
        fusion = (self._config or {}).get("cli_fusion") or {}

        grok = params.get("grok") or hc.get("grok") or fusion.get("default_cli")
        panel = params.get(support.PARAM_PANEL) or hc.get("panel")
        judge = params.get(support.PARAM_JUDGE) or hc.get("judge")
        if not panel:
            preset = (fusion.get("presets") or {}).get(fusion.get("default_preset")) or {}
            panel = preset.get("panel")
            judge = judge or preset.get("judge")

        known = set(registry.names())
        # grok defaults to the first available CLI if still unset.
        if not grok:
            avail = registry.available() or registry.names()
            grok = avail[0] if avail else None
        if grok and grok not in known:
            grok = None
        panel = [n for n in (panel or []) if n in known]
        if judge and judge not in known:
            judge = None
        return grok, panel, judge

    # --- the REST step (deterministic under SWARM_TEST_MODE) -------------- #

    async def _rest_reason(self, prompt: str) -> str:
        """A single REST-style LLM reasoning call (the coordinator).

        Under ``SWARM_TEST_MODE`` we return a fixed stub so the REST half is
        deterministic with no network — the same idiom blueprint_gawd /
        blueprint_zeus use. Replace the body below with a real OpenAI/Anthropic
        client call in production.
        """
        if os.environ.get("SWARM_TEST_MODE"):
            return f"[rest-plan] {prompt}"
        # Real REST reasoning: one openai-agents Agent (the LLM coordinator). It
        # degrades gracefully — if no LLM is configured/reachable, the CLI half
        # still runs — so a missing key never sinks the whole hybrid.
        try:
            from agents import Runner

            agent = self.make_agent(
                name="Coordinator",
                instructions=(
                    "You are a planning coordinator. In 1-2 sentences, give a brief "
                    "plan for answering the user's request — what to check and which "
                    "sub-questions to delegate."
                ),
                tools=[],
            )
            result = await Runner.run(agent, prompt)
            return str(result.final_output)
        except Exception as exc:  # noqa: BLE001 — degrade, don't crash the run
            return f"[rest-plan unavailable: {exc}] {prompt}"

    # --- entry point ------------------------------------------------------ #

    async def run(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        # Snapshot params before any await (a cached instance may be shared).
        params = dict(self._params)

        prompt = support.render_prompt(messages)
        if not prompt:
            yield support.message_chunk("No prompt provided.", final=True)
            return

        registry = support.apply_overrides(support.build_registry(self._config), params)
        grok_name, panel_names, judge_name = self._resolve(params, registry)
        workdir = params.get(support.PARAM_WORKDIR)

        # ---- 1. REST reasoning step (the coordinator's master plan) ------ #
        yield support.progress_chunk("_Coordinator reasoning (REST step)…_")
        plan = await self._rest_reason(prompt)
        # The REST plan steers the CLI sub-questions below.
        sub_question = f"{prompt}\n\n--- Plan ---\n{plan}"

        # ---- 2. grok CLI persona step ------------------------------------ #
        grok_answer = ""
        if grok_name:
            yield support.progress_chunk(f"_Delegating to the grok persona (`{grok_name}`)…_")
            ask_grok = cli_persona(registry.get(grok_name))  # async (str) -> str
            grok_answer = await ask_grok(sub_question)
            # cli_persona never raises: failures arrive as "[<name> unavailable: …]".

        # ---- 3. consensus panel step ------------------------------------- #
        consensus_answer = ""
        if panel_names:
            yield support.progress_chunk(
                f"_Escalating to consensus over {', '.join(panel_names)}…_"
            )
            panel = registry.resolve_panel(panel_names)
            judge = registry.get(judge_name) if judge_name else None

            if workdir:
                # Full ConsensusResult path: surface per-panelist failures, honour workdir.
                cons = await run_consensus(
                    sub_question, panel, judge,
                    workdirs={n: workdir for n in registry.names()},
                )
                for r in cons.results:
                    if not r.ok:
                        yield support.progress_chunk(f"_• {r.name} failed: {r.error}_")
                consensus_answer = cons.answer or "(no consensus reached)"
            else:
                # Granular tool callable: collapse the panel -> one answer.
                consensus = consensus_fn(panel, judge)  # async (str) -> str
                consensus_answer = await consensus(sub_question)

        # ---- 4. combine REST + CLI outputs into the final answer --------- #
        parts = [f"REST plan:\n{plan}"]
        if grok_answer:
            parts.append(f"grok persona:\n{grok_answer}")
        if consensus_answer:
            parts.append(f"Consensus:\n{consensus_answer}")
        if not (grok_answer or consensus_answer):
            parts.append(
                "(no CLI agents configured — add a 'cli_agents' block; see docs/CLI_FUSION.md)"
            )

        yield support.message_chunk("\n\n".join(parts), final=True)
