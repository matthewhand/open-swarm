"""CLI Fusion blueprint — multi-CLI deliberation over the OpenAI API.

Fans a prompt out to a *panel* of configured agentic CLIs in parallel, has a
*judge* CLI compare their outputs into a structured analysis, *synthesizes* a
final answer, and (optionally) drives a bounded *master-plan loop* that feeds
the judge's "next step" back into another round.

Inspired by OpenRouter Fusion, but the panelists are whatever CLI agents the
operator has installed (``claude``, ``gemini``, ``codex``, ...). Selection is
config/preset driven; see ``docs/CLI_FUSION.md``.

Request model: ``model: "cli_fusion"``. Per-request ``params`` may set
``panel`` (list), ``preset``, ``judge``, ``max_rounds``, ``timeout``, ``workdir``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import tempfile
from typing import Any, AsyncIterator, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.cli_adapter import CliAdapterRegistry, CliResult

logger = logging.getLogger(__name__)

# Bound the master-plan loop regardless of config, to cap cost/runaway.
MAX_ROUNDS_CEILING = 5
# Default cap on how many CLI subprocesses launch at once (each may spawn a tree).
DEFAULT_MAX_CONCURRENCY = 8
# Env flag used to stop a panelist that is itself a swarm fusion from re-fusing.
DEPTH_ENV = "SWARM_CLI_FUSION_DEPTH"

JUDGE_TEMPLATE = """You are the JUDGE in a multi-agent panel. The user's request was:

<request>
{prompt}
</request>

Several independent agents answered it. Compare (do NOT merely concatenate) their answers below.

{panel}

Return ONLY a JSON object with these keys:
- "consensus": list of points the agents agree on
- "contradictions": list of points where they disagree
- "gaps": list of things no agent covered
- "unique_insights": list of valuable points raised by a single agent
- "answer": a single best synthesized answer combining the strongest reasoning from all agents
- "done": boolean — true if "answer" fully resolves the request, false if another round of work is needed
- "next_step": if not done, one concrete instruction for the next round (else "")
"""


def _safe_json(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from CLI output, tolerating surrounding prose."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# --- Per-panelist workdir isolation --------------------------------------- #

_SLUG_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _slug(name: str) -> str:
    """A filesystem-safe fragment for temp-dir names."""
    return _SLUG_RE.sub("-", name)[:40] or "panel"


async def _run_git(*args: str) -> tuple[int, str]:
    """Run ``git`` and return (returncode, combined output). Never raises."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except (OSError, ValueError):
        return 127, ""
    out, _ = await proc.communicate()
    return (proc.returncode or 0), (out or b"").decode("utf-8", errors="replace")


async def _is_git_repo(path: str) -> bool:
    rc, out = await _run_git("-C", path, "rev-parse", "--is-inside-work-tree")
    return rc == 0 and out.strip() == "true"


async def _worktree_add(repo: str, path: str) -> bool:
    rc, _ = await _run_git("-C", repo, "worktree", "add", "--detach", "--quiet", path, "HEAD")
    return rc == 0


async def _worktree_remove(repo: str, path: str) -> None:
    await _run_git("-C", repo, "worktree", "remove", "--force", path)


async def _should_isolate(
    base_workdir: str | None, panel_names: list[str], setting: bool | None
) -> bool:
    """Decide whether panelists get private workdirs.

    ``setting`` is the resolved ``isolate`` value: ``False`` never isolates,
    ``True`` always isolates, ``None`` (auto) isolates only a multi-panelist run
    whose ``workdir`` is a git repo (cheap, safe worktrees; nothing to gain on a
    single panelist).
    """
    if setting is False:
        return False
    if setting is True:
        return True
    return len(panel_names) > 1 and bool(base_workdir) and await _is_git_repo(base_workdir)


@contextlib.asynccontextmanager
async def _panel_workspaces(
    base_workdir: str | None, panel_names: list[str], isolate: bool
) -> AsyncIterator[dict[str, str | None]]:
    """Yield a ``name -> workdir`` map, isolating panelists when asked.

    When isolating: a git ``base_workdir`` gives each panelist a throwaway
    ``git worktree`` at HEAD (sees the repo, edits stay private); otherwise each
    gets a fresh empty temp dir. All scratch is removed on exit. When not
    isolating, every panelist shares ``base_workdir``.
    """
    if not isolate:
        yield {name: base_workdir for name in panel_names}
        return

    is_repo = bool(base_workdir) and await _is_git_repo(base_workdir)
    roots: list[str] = []
    worktrees: list[tuple[str, str]] = []
    mapping: dict[str, str | None] = {}
    try:
        for name in panel_names:
            root = tempfile.mkdtemp(prefix=f"swarm-fusion-{_slug(name)}-")
            roots.append(root)
            if is_repo:
                tree = os.path.join(root, "tree")
                if await _worktree_add(base_workdir, tree):  # type: ignore[arg-type]
                    mapping[name] = tree
                    worktrees.append((base_workdir, tree))  # type: ignore[arg-type]
                    continue
            mapping[name] = root  # non-repo (or worktree failed): empty scratch dir
        yield mapping
    finally:
        for repo, tree in worktrees:
            await _worktree_remove(repo, tree)
        for root in roots:
            shutil.rmtree(root, ignore_errors=True)


class CliFusionBlueprint(BlueprintBase):
    """Panel → judge → synthesize, with an optional bounded master-plan loop."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "cli_fusion",
        "title": "CLI Fusion (multi-CLI deliberation)",
        "description": (
            "Fan a prompt to a panel of configured agentic CLIs in parallel, "
            "judge and synthesize their answers, and optionally iterate a "
            "master plan. OpenRouter-Fusion-style, with your installed CLIs."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "fusion", "multi-agent", "deliberation", "openai-compatible"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "cli_fusion", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    # --- helpers -------------------------------------------------------- #

    def _max_rounds(self, params: dict[str, Any], fusion_cfg: dict[str, Any]) -> int:
        raw = params.get("max_rounds", fusion_cfg.get("max_rounds", 1))
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 1
        return max(1, min(n, MAX_ROUNDS_CEILING))

    async def _run_panel(
        self,
        registry: CliAdapterRegistry,
        panel_names: list[str],
        prompt: str,
        workdirs: dict[str, str | None],
        child_env: dict[str, str],
        max_concurrency: int,
    ) -> list[CliResult]:
        panel = registry.resolve_panel(panel_names)
        sem = asyncio.Semaphore(max(1, max_concurrency))

        async def _bounded(adapter):
            async with sem:
                return await adapter.run(
                    prompt, workdir=workdirs.get(adapter.name), extra_env=child_env
                )

        return await asyncio.gather(*(_bounded(a) for a in panel))

    async def _judge(
        self,
        registry: CliAdapterRegistry,
        judge_name: str | None,
        prompt: str,
        results: list[CliResult],
        workdir: str | None,
        child_env: dict[str, str],
    ) -> dict[str, Any] | None:
        if not judge_name:
            return None
        try:
            judge = registry.get(judge_name)
        except Exception:
            return None
        panel_text = "\n\n".join(f"### Agent: {r.name}\n{r.text}" for r in results)
        judge_prompt = JUDGE_TEMPLATE.format(prompt=prompt, panel=panel_text)
        res = await judge.run(judge_prompt, workdir=workdir, extra_env=child_env)
        if not res.ok:
            logger.warning("Judge %s failed: %s", judge_name, res.error)
            return None
        return _safe_json(res.text)

    @staticmethod
    def _synthesize(analysis: dict[str, Any] | None, results: list[CliResult]) -> str:
        if analysis and isinstance(analysis.get("answer"), str) and analysis["answer"].strip():
            return analysis["answer"].strip()
        # No usable judge analysis: fall back to the longest successful answer.
        best = max(results, key=lambda r: len(r.text or ""))
        return best.text

    def _format_final(
        self,
        params: dict[str, Any],
        answer: str,
        analysis: dict[str, Any] | None,
        results: list[CliResult],
        rounds: int,
    ) -> str:
        show = params.get("show_analysis")
        if show is None:
            show = ((self._config or {}).get("cli_fusion") or {}).get("show_analysis", False)
        if not show:
            return answer
        lines = [answer, "", "---", f"_Fusion: {len(results)} agents, {rounds} round(s)._"]
        if analysis:
            for key in ("consensus", "contradictions", "gaps", "unique_insights"):
                vals = analysis.get(key)
                if vals:
                    rendered = "; ".join(str(v) for v in vals) if isinstance(vals, list) else str(vals)
                    lines.append(f"- **{key}**: {rendered}")
        return "\n".join(lines)

    # --- entry point ---------------------------------------------------- #

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        # Snapshot params once before any await (see blueprint_cli_agent for why):
        # a cached singleton instance may be shared across concurrent requests.
        params = dict(self._params)

        prompt = support.render_prompt(messages)
        if not prompt:
            yield support.message_chunk("No prompt provided.", final=True)
            return

        registry = support.apply_overrides(support.build_registry(self._config), params)
        panel_names, judge_name = support.resolve_panel(self._config, params, registry)
        if not panel_names:
            yield support.message_chunk(
                "No CLI agents are configured for fusion. Add a 'cli_agents' block "
                "and a 'cli_fusion' preset to your swarm config (see docs/CLI_FUSION.md).",
                final=True,
            )
            return

        fusion_cfg = (self._config or {}).get("cli_fusion") or {}
        workdir = params.get(support.PARAM_WORKDIR)
        isolate_setting = params.get(support.PARAM_ISOLATE)
        if isolate_setting is None:
            isolate_setting = fusion_cfg.get("isolate_workdir")  # may stay None (=auto)
        try:
            max_concurrency = int(
                params.get("max_concurrency", fusion_cfg.get("max_concurrency", DEFAULT_MAX_CONCURRENCY))
            )
        except (TypeError, ValueError):
            max_concurrency = DEFAULT_MAX_CONCURRENCY

        # Recursion guard: if we are running *inside* another fusion (a panelist
        # was itself a swarm fusion blueprint), degrade to a single panelist with
        # no further fan-out so the tree cannot explode.
        depth = 0
        try:
            depth = int(os.environ.get(DEPTH_ENV, "0"))
        except ValueError:
            depth = 0
        if depth >= 1:
            panel_names = panel_names[:1]
            judge_name = None
            max_rounds = 1
            yield support.progress_chunk("_Nested fusion detected; running a single agent._")
        else:
            max_rounds = self._max_rounds(params, fusion_cfg)
        child_env = {DEPTH_ENV: str(depth + 1)}

        isolate = await _should_isolate(workdir, panel_names, isolate_setting)

        current_prompt = prompt
        for round_i in range(max_rounds):
            yield support.progress_chunk(
                f"_Round {round_i + 1}/{max_rounds}: consulting {len(panel_names)} "
                f"CLI agent(s): {', '.join(panel_names)}…_"
            )
            if isolate:
                yield support.progress_chunk(
                    f"_Isolating {len(panel_names)} panelist(s) into private workdirs…_"
                )
            # Fresh per-panelist workspaces each round; torn down before judging
            # (the judge runs in the base workdir, only comparing text answers).
            async with _panel_workspaces(workdir, panel_names, isolate) as workdirs:
                results = await self._run_panel(
                    registry, panel_names, current_prompt, workdirs, child_env, max_concurrency
                )
            for r in results:
                if not r.ok:
                    yield support.progress_chunk(f"_• {r.name} failed: {r.error}_")
            ok_results = [r for r in results if r.ok]
            if not ok_results:
                yield support.message_chunk("All CLI panelists failed.", final=True)
                return

            if judge_name:
                yield support.progress_chunk(f"_Judging {len(ok_results)} response(s) with `{judge_name}`…_")
            analysis = await self._judge(
                registry, judge_name, current_prompt, ok_results, workdir, child_env
            )
            answer = self._synthesize(analysis, ok_results)
            done = bool(analysis.get("done", True)) if analysis else True

            if done or round_i == max_rounds - 1:
                yield support.message_chunk(
                    self._format_final(params, answer, analysis, ok_results, rounds=round_i + 1),
                    final=True,
                )
                return

            next_step = (analysis or {}).get("next_step") or "Refine and improve the answer."
            yield support.progress_chunk(f"_Master plan → next step: {str(next_step)[:100]}_")
            current_prompt = (
                f"{prompt}\n\n--- Prior synthesized answer ---\n{answer}\n\n"
                f"--- Next step ---\n{next_step}"
            )
