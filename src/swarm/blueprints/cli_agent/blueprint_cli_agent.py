"""CLI Agent blueprint — expose a single configured agentic CLI over the
OpenAI-compatible API.

This is the minimal drop-in: a request to ``model: "cli_agent"`` runs one
configured CLI (``claude``, ``gemini``, ...) one-shot and streams its answer
back as a normal chat completion. Which CLI runs is chosen by (in order) the
per-request ``cli`` param, the config ``cli_fusion.default_cli``, or the first
CLI actually installed on this host.

See :mod:`swarm.core.cli_adapter` for the lifecycle layer and
``cli_fusion`` for multi-CLI deliberation.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.cli_adapter import CliAdapter, CliResult
from swarm.core.cli_sessions import (
    clear_cli_session,
    get_cli_session,
    is_resume_failure,
    put_cli_session,
    resolve_thread,
)
from swarm.core.consensus import run_consensus

logger = logging.getLogger(__name__)


class CliAgentBlueprint(BlueprintBase):
    """Run one configured agentic CLI as an OpenAI-compatible model."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "cli_agent",
        "title": "CLI Agent (single external CLI)",
        "description": (
            "Expose a single configured agentic CLI (claude, gemini, codex, ...) "
            "over the OpenAI-compatible API. The 'cli' param selects which one."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["cli", "subagent", "adapter", "openai-compatible"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "cli_agent", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        """Capture per-request params forwarded by the API view."""
        self._params = dict(params or {})

    def _thread_ref(self, params: dict[str, Any]) -> tuple[str, str] | None:
        return resolve_thread(params, default_agent=self.blueprint_id)

    def _stored_session(self, params: dict[str, Any], cli_name: str) -> str | None:
        ref = self._thread_ref(params)
        if ref is None:
            return None
        return get_cli_session(ref[0], ref[1], cli_name)

    def _remember_session(
        self, params: dict[str, Any], cli_name: str, session_id: str | None
    ) -> None:
        ref = self._thread_ref(params)
        if ref is None:
            return
        put_cli_session(
            ref[0],
            ref[1],
            cli_name,
            session_id,
            conversation_id=str(params.get("conversation_id") or ""),
        )

    def _forget_session(self, params: dict[str, Any], cli_name: str) -> None:
        ref = self._thread_ref(params)
        if ref is None:
            return
        clear_cli_session(
            ref[0],
            ref[1],
            cli_name,
            conversation_id=str(params.get("conversation_id") or ""),
        )

    def _turn_prompt(
        self,
        messages: list[dict[str, Any]],
        full_prompt: str,
        params: dict[str, Any],
        workdir: str | None,
        *,
        resume: bool,
    ) -> str:
        if not resume:
            return full_prompt
        latest = support.latest_user_prompt(messages)
        if not latest:
            return full_prompt
        prompt, _applied = support.apply_skill_to_prompt(latest, params, workdir=workdir)
        return prompt

    async def _invoke_cli(
        self,
        adapter: CliAdapter,
        messages: list[dict[str, Any]],
        full_prompt: str,
        params: dict[str, Any],
        workdir: str | None,
    ) -> tuple[CliResult, bool]:
        """Run one CLI, replaying a stored session id when the CLI can resume.

        Returns ``(result, resumed)``. ``resumed`` is True only when a stored
        id was passed and the run succeeded without falling back to a new session.
        """
        stored = self._stored_session(params, adapter.name)
        can_resume = bool(stored and adapter.can_resume())
        prompt = self._turn_prompt(
            messages, full_prompt, params, workdir, resume=can_resume
        )
        result = await adapter.run(
            prompt, workdir=workdir, session_id=stored if can_resume else None
        )
        resumed = can_resume and result.ok
        if can_resume and not result.ok and is_resume_failure(result):
            self._forget_session(params, adapter.name)
            prompt = self._turn_prompt(
                messages, full_prompt, params, workdir, resume=False
            )
            result = await adapter.run(prompt, workdir=workdir, session_id=None)
            resumed = False
        if result.session_id:
            self._remember_session(params, adapter.name, result.session_id)
        elif resumed and stored:
            self._remember_session(params, adapter.name, stored)
        return result, resumed

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        # Snapshot params once before any await: the API view may reuse a cached
        # singleton instance for param-less requests, so self._params can be
        # mutated by a concurrent request across await points.
        params = dict(self._params)

        # A blueprint can declare desired inference traits in its metadata
        # ("inference_profile") instead of naming a CLI; honor it unless the
        # request explicitly set a cli or its own profile.
        if support.PARAM_CLI not in params and support.PARAM_PROFILE not in params:
            bp_profile = self.metadata.get("inference_profile")
            if bp_profile:
                params[support.PARAM_PROFILE] = bp_profile

        prompt = support.render_prompt(messages)
        if not prompt:
            yield support.message_chunk("No prompt provided.", final=True)
            return

        # Optional skill: `skill=<name>` prepends a discovered skill's
        # instructions to the prompt (portable across whichever CLI runs) and
        # stages any bundled assets into the workdir for write-mode CLIs.
        from swarm.core.workdir import WorkdirEscapeError

        try:
            workdir = support.resolve_workdir(params)
        except WorkdirEscapeError as e:
            yield support.message_chunk(str(e), final=True)
            return

        if params.get(support.PARAM_SKILL):
            prompt, applied = support.apply_skill_to_prompt(
                prompt, params, workdir=workdir
            )
            if applied:
                yield support.progress_chunk(f"_Applying skill `{applied}`…_")
            else:
                yield support.progress_chunk(
                    f"_Skill `{params[support.PARAM_SKILL]}` not found — running without it._"
                )

        # Per-model inference-profile resolution: with a profile in play and
        # neither an explicit cli nor a default_cli set, resolve to the closest
        # (cli, model) and pin both — so e.g. a "deep reasoning" ask lands on
        # gemini's pro model, not its flash default.
        config = self._config
        default_cli = ((config or {}).get("cli_fusion") or {}).get("default_cli")
        desired = params.get(support.PARAM_PROFILE)
        if desired and not params.get(support.PARAM_CLI) and not default_cli:
            cli, model = support.resolve_profile_candidate(
                desired, config, support.build_registry(config)
            )
            if cli:
                params[support.PARAM_CLI] = cli
                if model:
                    from swarm.core import cli_catalog

                    agents = dict((config or {}).get("cli_agents") or {})
                    if cli in agents:
                        agents[cli] = cli_catalog.apply_model(agents[cli], cli, model)
                        config = {**config, "cli_agents": agents}
                    yield support.progress_chunk(
                        f"_Inference profile → `{cli}` model `{model}`…_"
                    )
                else:
                    yield support.progress_chunk(f"_Inference profile → `{cli}`…_")

        registry = support.apply_overrides(support.build_registry(config), params)
        chain = support.resolve_failover_chain(config, params, registry)
        if not chain:
            yield support.message_chunk(
                "No CLI agents are configured. Add a 'cli_agents' block to your "
                "swarm config (see docs/CLI_FUSION.md).",
                final=True,
            )
            return

        # Consensus agents: if the selected agent is designated as a consensus
        # agent (or the request asks for consensus), calling it runs a PANEL
        # instead of a single call. A per-request `consensus` param overrides the
        # agent's config designation (set it falsy to force a single call).
        selected = registry.get(chain[0])
        spec = params[support.PARAM_CONSENSUS] if support.PARAM_CONSENSUS in params else selected.config.consensus
        panel_spec = support.resolve_consensus_spec(spec, selected.name, registry)
        if panel_spec is not None:
            panel_names, judge_name = panel_spec
            yield support.progress_chunk(
                f"_`{selected.name}` is a consensus agent → panel: {', '.join(panel_names)} "
                f"(judge: {judge_name or 'none'})…_"
            )
            panel = registry.resolve_panel(panel_names)
            judge = registry.get(judge_name) if judge_name else None
            cons = await run_consensus(
                prompt, panel, judge, workdirs=dict.fromkeys(registry.names(), workdir)
            )
            for r in cons.results:
                if not r.ok:
                    yield support.progress_chunk(f"_• {r.name} failed: {r.error}_")
            yield support.message_chunk(
                cons.answer or "All consensus panelists failed.",
                final=True,
                meta=support.backend_meta([r.name for r in cons.ok_results], judge_name),
            )
            return

        # Streaming-text fast path: stream the first *installed* candidate
        # incrementally. No mid-stream failover — once bytes are on the wire we
        # can't unsend them — so this commits to one CLI.
        if kwargs.get("stream"):
            target = next((n for n in chain if registry.get(n).is_available()), None)
            if target is not None and (registry.get(target).config.parse or "text") == "text":
                adapter = registry.get(target)
                yield support.progress_chunk(f"_Streaming CLI agent `{target}`…_")
                stored = self._stored_session(params, adapter.name)
                can_resume = bool(stored and adapter.can_resume())
                turn_prompt = self._turn_prompt(
                    messages, prompt, params, workdir, resume=can_resume
                )
                result = None
                async for chunk in adapter.stream_run(
                    turn_prompt,
                    workdir=workdir,
                    session_id=stored if can_resume else None,
                ):
                    if chunk.final:
                        result = chunk.result
                    elif chunk.delta:
                        yield support.message_chunk(chunk.delta)  # incremental delta
                resumed = can_resume and result is not None and result.ok
                if result is not None and can_resume and not result.ok and is_resume_failure(result):
                    self._forget_session(params, adapter.name)
                    turn_prompt = self._turn_prompt(
                        messages, prompt, params, workdir, resume=False
                    )
                    result = None
                    async for chunk in adapter.stream_run(turn_prompt, workdir=workdir):
                        if chunk.final:
                            result = chunk.result
                        elif chunk.delta:
                            yield support.message_chunk(chunk.delta)
                    resumed = False
                if result is not None and result.session_id:
                    self._remember_session(params, adapter.name, result.session_id)
                elif resumed and stored:
                    self._remember_session(params, adapter.name, stored)
                yield support.session_notice_chunk(adapter.name, resumed=resumed)
                if result is None or not result.ok:
                    err = (result.error if result else None) or "unknown error"
                    yield support.message_chunk(support.format_cli_error(adapter, err), final=True)
                elif result.parse_error:
                    logger.warning("CLI %s parse issue: %s", target, result.parse_error)
                # On success the content was already streamed as deltas.
                return
            # json-parse target (or nothing installed): fall through to failover.

        # Non-streaming (and json-in-stream): try each candidate, first ok wins.
        last: tuple[str, str] | None = None
        for name in chain:
            adapter = registry.get(name)
            if not adapter.is_available():
                yield support.progress_chunk(f"_Skipping `{name}` (not installed); failing over…_")
                continue
            yield support.progress_chunk(f"_Running CLI agent `{name}`…_")
            result, resumed = await self._invoke_cli(
                adapter, messages, prompt, params, workdir
            )
            yield support.session_notice_chunk(adapter.name, resumed=resumed)
            if result.ok:
                if result.parse_error:
                    logger.warning("CLI %s parse issue: %s", name, result.parse_error)
                yield support.message_chunk(result.text, final=True, meta=support.backend_meta([name]))
                return
            last = (name, result.error or "unknown error")
            yield support.progress_chunk(f"_`{name}` failed: {last[1]} — failing over…_")

        detail = f" (last — {last[0]}: {last[1]})" if last else ""
        yield support.message_chunk(f"All CLI candidates failed{detail}.", final=True)
