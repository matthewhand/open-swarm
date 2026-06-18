"""Persona Council blueprint — diverse-lens consensus.

The functional cousin of the parody persona teams: instead of joke characters,
a *council* is a panel where each member is the same backend wearing a distinct
**expert lens** (a system-prompt persona). One question is examined through every
lens in parallel, then a judge reconciles them — reporting agreement, genuine
disagreement, and a synthesized position with the trade-offs named.

Consensus here comes from *perspective diversity*, not redundancy: a Utilitarian
and a Kantian disagree in useful ways a single run never surfaces.

Request model: ``model: "persona_council"``. Pick a council with
``params.council`` (e.g. ``ethics``, ``science``, ``psych``, ``decision``,
``red_team``) — built-in rosters need no config. A config block
``persona_council`` may add/override ``councils`` and set ``cli`` (which backend
wears the lenses) / ``judge`` / ``default_council``. Per-request ``params`` may
also pass an explicit ``personas`` roster (``[{"name": ..., "lens": ...}, ...]``).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.cli_adapter import CliAdapterRegistry

logger = logging.getLogger(__name__)

MAX_CONCURRENCY = 8
MAX_PERSONAS = 8

LENS_TEMPLATE = """Adopt the following perspective and answer ONLY from within it:
<perspective>
{lens}
</perspective>

Question:
{question}

Give your view in 2-4 sentences. Emphasize what THIS perspective notices that
others might miss. Do not hedge by listing other viewpoints — argue your lens.
"""

JUDGE_TEMPLATE = """You are moderating a council that examined one question through distinct
expert lenses. Here are their views:

{views}

Synthesize, do NOT merely concatenate:
1. Where the lenses genuinely agree.
2. The real tensions or disagreements between them.
3. A reasoned overall position that names the key trade-off.
Be concise. Return only the synthesis.
"""

# Built-in councils — each persona is a name + a system-prompt lens. These ship
# in code so `model: persona_council` works with zero config; a config
# `persona_council.councils` block extends/overrides them.
COUNCILS: dict[str, list[dict[str, str]]] = {
    "ethics": [
        {"name": "Utilitarian", "lens": "You are a strict utilitarian (Mill/Bentham). Judge purely by aggregate well-being and consequences; quantify who gains and loses."},
        {"name": "Kantian", "lens": "You are a Kantian deontologist. Judge by universalizable duties and treating persons as ends, never merely as means."},
        {"name": "Virtue", "lens": "You are an Aristotelian virtue ethicist. Ask what a person of good character would do and which virtues or vices are in play."},
        {"name": "Rawlsian", "lens": "You are a Rawlsian. Judge from behind the veil of ignorance: is this just for the least advantaged?"},
        {"name": "Care", "lens": "You are a care ethicist. Center relationships, dependency, and concrete responsibilities to specific people."},
    ],
    "science": [
        {"name": "Physicist", "lens": "Analyze as a physicist: mechanisms, energy, scale, what is conserved, order-of-magnitude estimates."},
        {"name": "EvolBiologist", "lens": "Analyze as an evolutionary biologist: selection pressures, function, trade-offs, variation."},
        {"name": "Complexity", "lens": "Analyze as a complexity and systems scientist: feedback loops, emergence, nonlinearity, second-order effects."},
        {"name": "Statistician", "lens": "Analyze as a skeptical statistician: base rates, confounders, sample issues, and what evidence would falsify the claim."},
        {"name": "Experimentalist", "lens": "Analyze as an experimentalist: propose the single most decisive, falsifiable test."},
    ],
    "psych": [
        {"name": "Cognitive", "lens": "Analyze through cognitive/CBT: beliefs, appraisals, biases, and how thought patterns get reinforced."},
        {"name": "Psychodynamic", "lens": "Analyze through psychodynamic theory: unconscious motives, defenses, early relational patterns."},
        {"name": "Behaviorist", "lens": "Analyze through behaviorism: antecedents, reinforcement contingencies, observable conditioning."},
        {"name": "Evolutionary", "lens": "Analyze through evolutionary psychology: adaptive function and ancestral-environment mismatch."},
        {"name": "Social", "lens": "Analyze through social and systems psychology: norms, roles, situational forces, group dynamics."},
    ],
    "decision": [
        {"name": "FirstPrinciples", "lens": "Reason from first principles: strip the problem to fundamentals and rebuild."},
        {"name": "SecondOrder", "lens": "Trace second- and third-order consequences: and then what happens?"},
        {"name": "OutsideView", "lens": "Take the outside view: base rates and reference classes, not the inside story."},
        {"name": "DevilsAdvocate", "lens": "Argue the strongest case AGAINST the obvious choice."},
        {"name": "PreMortem", "lens": "Run a pre-mortem: assume it failed badly; explain why."},
    ],
    "red_team": [
        {"name": "Security", "lens": "Attack as a security engineer: trust boundaries, abuse cases, injection, escalation."},
        {"name": "SRE", "lens": "Attack as an SRE: failure modes, partial outages, retries, blast radius, what pages at 3am."},
        {"name": "Legal", "lens": "Attack as legal/compliance: liability, consent, data handling, regulatory exposure."},
        {"name": "Safety", "lens": "Attack as a safety/ethics reviewer: harms, misuse, who is hurt if this is wrong."},
        {"name": "FirstToBreak", "lens": "Name the single thing that breaks first in the real world, and why."},
    ],
}
DEFAULT_COUNCIL = "ethics"


class PersonaCouncilBlueprint(BlueprintBase):
    """Examine a question through diverse expert lenses, then reconcile."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "persona_council",
        "title": "Persona Council (diverse-lens consensus)",
        "description": (
            "Examine one question through a council of distinct expert lenses "
            "(ethics, science, psych, decision, red_team) in parallel, then a "
            "judge synthesizes agreement, tensions, and a position. Consensus "
            "from perspective diversity, not redundancy."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "consensus", "personas", "council", "openai-compatible"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "persona_council", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    def _councils(self) -> dict[str, list[dict[str, str]]]:
        merged = {k: list(v) for k, v in COUNCILS.items()}
        cfg = (self._config or {}).get("persona_council") or {}
        for name, roster in (cfg.get("councils") or {}).items():
            if isinstance(roster, list):
                merged[name] = roster
        return merged

    def _resolve(
        self, params: dict[str, Any], registry: CliAdapterRegistry
    ) -> tuple[list[dict[str, str]], str, str | None]:
        """Resolve (personas, runner_cli, judge_cli)."""
        cfg = (self._config or {}).get("persona_council") or {}
        fusion = (self._config or {}).get("cli_fusion") or {}

        # personas: explicit roster > named council > config default > built-in default
        personas = params.get("personas")
        if not isinstance(personas, list) or not personas:
            councils = self._councils()
            name = params.get("council") or cfg.get("default_council") or DEFAULT_COUNCIL
            personas = councils.get(name) or councils.get(DEFAULT_COUNCIL) or []
        personas = [p for p in personas if isinstance(p, dict) and p.get("lens")][:MAX_PERSONAS]

        known = set(registry.names())
        # runner: which backend wears the lenses (one model, N hats by default)
        runner = params.get(support.PARAM_CLI) or cfg.get("cli") or fusion.get("default_cli")
        if runner not in known:
            avail = registry.available() or registry.names()
            runner = next((c for c in ("claude", "grok", "gemini") if c in avail), (avail[0] if avail else None))
        judge = params.get(support.PARAM_JUDGE) or cfg.get("judge") or runner
        if judge and judge not in known:
            judge = runner
        return personas, runner, judge

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        params = dict(self._params)

        question = support.render_prompt(messages)
        if not question:
            yield support.message_chunk("No prompt provided.", final=True)
            return

        registry = support.apply_overrides(support.build_registry(self._config), params)
        personas, runner, judge = self._resolve(params, registry)
        if not personas:
            yield support.message_chunk("No council personas resolved.", final=True)
            return
        if not runner:
            yield support.message_chunk(
                "No CLI backend is configured to run the council. Add a 'cli_agents' "
                "block to your swarm config (see docs/CLI_FUSION.md).",
                final=True,
            )
            return

        workdir = params.get(support.PARAM_WORKDIR)
        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        names = ", ".join(p["name"] for p in personas)
        yield support.progress_chunk(
            f"_Council of {len(personas)} lenses ({names}) on `{runner}`, judged by `{judge or 'none'}`…_"
        )

        async def _one(persona: dict[str, str]):
            adapter = registry.get(runner)
            prompt = LENS_TEMPLATE.format(lens=persona["lens"], question=question)
            async with sem:
                res = await adapter.run(prompt, workdir=workdir)
            return persona["name"], res

        results = await asyncio.gather(*(_one(p) for p in personas))
        views = [(name, res.text) for name, res in results if res.ok and res.text.strip()]
        for name, res in results:
            if not (res.ok and res.text.strip()):
                yield support.progress_chunk(f"_• lens {name} produced nothing ({res.error or 'empty'})._")
        if not views:
            yield support.message_chunk("Every council lens failed.", final=True)
            return

        block = "\n\n".join(f"### {name}\n{text}" for name, text in views)
        meta = support.backend_meta([runner], judge=judge)

        if judge:
            yield support.progress_chunk(f"_Reconciling {len(views)} lens(es) with `{judge}`…_")
            jres = await registry.get(judge).run(
                JUDGE_TEMPLATE.format(views=block), workdir=workdir
            )
            if jres.ok and jres.text.strip():
                answer = jres.text
                if params.get("show_analysis"):
                    answer = f"{answer}\n\n---\n_Council views ({len(views)} lenses):_\n\n{block}"
                yield support.message_chunk(answer, final=True, meta=meta)
                return
            yield support.progress_chunk(f"_Judge failed ({jres.error}); returning the lens views._")
        yield support.message_chunk(block, final=True, meta=meta)
