"""Shared helpers for the CLI-agent blueprints (``cli_agent`` and ``cli_fusion``).

Keeps prompt rendering, adapter-registry construction, panelist selection, and
the chunk shapes blueprints yield in one place so the single-CLI and fusion
blueprints stay consistent.
"""

from __future__ import annotations

import logging
from typing import Any

from swarm.core.cli_adapter import CliAdapter, CliAdapterRegistry

logger = logging.getLogger(__name__)

# Per-request param keys recognised across the CLI blueprints.
PARAM_CLI = "cli"            # single-CLI: which adapter to run
PARAM_PANEL = "panel"        # fusion: list of adapter names
PARAM_PRESET = "preset"      # fusion: named preset
PARAM_JUDGE = "judge"        # fusion: judge adapter/profile
PARAM_TIMEOUT = "timeout"    # override adapter timeout (seconds)
PARAM_WORKDIR = "workdir"    # working directory for the CLI(s)
PARAM_ISOLATE = "isolate"    # fusion: per-panelist workdir isolation (bool)
PARAM_FALLBACK = "fallback"  # single-CLI: explicit ordered failover list
PARAM_FAILOVER = "failover"  # single-CLI: enable auto-failover (default True)
PARAM_CONSENSUS = "consensus"  # single-CLI: per-request consensus override (bool/int/list/dict)
PARAM_SKILL = "skill"        # apply a named skill's instructions to the prompt
PARAM_PROFILE = "profile"    # desired inference traits {intelligence,speed,cost} 0..1


def render_prompt(messages: list[dict[str, Any]]) -> str:
    """Flatten an OpenAI-style message list into a single prompt string.

    A lone user message is passed through verbatim. A multi-turn conversation
    is rendered as a simple ``ROLE: content`` transcript so a one-shot CLI sees
    the full context.
    """
    msgs = [m for m in (messages or []) if isinstance(m, dict) and m.get("content")]
    if not msgs:
        return ""
    if len(msgs) == 1:
        return str(msgs[0]["content"]).strip()
    lines = []
    for m in msgs:
        role = (m.get("role") or "user").upper()
        lines.append(f"{role}: {str(m['content']).strip()}")
    return "\n\n".join(lines)


def apply_skill_to_prompt(
    prompt: str, params: dict[str, Any] | None, workdir: str | None = None
) -> tuple[str, str | None]:
    """Apply a named skill (``params['skill']``) to ``prompt``.

    Returns ``(prompt, applied_name)``. With no skill requested, the prompt is
    unchanged and ``applied_name`` is None. An unknown skill name also leaves
    the prompt unchanged (the caller can warn) — we never fail the run over a
    bad skill name. Skills load from the standard ``skills/`` directory.

    When ``workdir`` is given and the skill bundles assets (scripts/templates),
    they are copied into ``workdir`` so a write-mode CLI can read or execute them.
    """
    name = (params or {}).get(PARAM_SKILL)
    if not name:
        return prompt, None
    from swarm.core import skills  # lazy: only pay discovery cost when used

    skill = skills.discover_skills().get(name)
    if skill is None:
        return prompt, None
    if workdir and skill.assets:
        skills.stage_assets(skill, workdir)
    return skills.apply_skill(skill, prompt), skill.name


def build_registry(config: dict[str, Any] | None) -> CliAdapterRegistry:
    """Build the CLI adapter registry from the top-level swarm config."""
    return CliAdapterRegistry.from_config(config or {})


def _fusion_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return ((config or {}).get("cli_fusion") or {})


def select_single_cli(
    config: dict[str, Any] | None,
    params: dict[str, Any] | None,
    registry: CliAdapterRegistry,
) -> str | None:
    """Pick the adapter name for the single-CLI blueprint.

    Priority: per-request ``cli`` param > config ``cli_fusion.default_cli`` >
    first available-on-host adapter > first configured adapter. Returns None
    when no adapters are configured at all.
    """
    params = params or {}
    requested = params.get(PARAM_CLI)
    if requested:
        return requested
    # An explicit ``default_cli`` is a deliberate global choice and wins over a
    # blueprint's soft profile suggestion.
    default = _fusion_config(config).get("default_cli")
    if default:
        return default
    # Inference-profile match: a blueprint (or request) can declare *desired*
    # traits instead of naming a CLI; resolve to the closest available backend.
    # Opt-in — only engages when a profile is present and no default_cli is set.
    desired = params.get(PARAM_PROFILE) or _fusion_config(config).get("profile")
    if desired:
        picked = resolve_by_profile(desired, config, registry)
        if picked:
            return picked
    available = registry.available()
    if available:
        return available[0]
    names = registry.names()
    return names[0] if names else None


def candidate_traits(
    config: dict[str, Any] | None, registry: CliAdapterRegistry
) -> dict[str, dict[str, Any]]:
    """Capability traits per *available* CLI: config ``traits`` override catalog
    defaults. CLIs with neither known traits nor a config block are still
    included (neutral), so resolution always has candidates when CLIs exist.
    """
    from swarm.core import cli_catalog

    cli_agents = (config or {}).get("cli_agents") or {}
    out: dict[str, dict[str, Any]] = {}
    for name in registry.available():
        entry = cli_agents.get(name) or {}
        out[name] = entry.get("traits") or cli_catalog.cli_traits(name) or {}
    return out


def resolve_by_profile(
    desired: dict[str, Any] | None,
    config: dict[str, Any] | None,
    registry: CliAdapterRegistry,
) -> str | None:
    """Pick the available CLI whose traits best match ``desired``, or None."""
    from swarm.core import inference_profile

    candidates = candidate_traits(config, registry)
    return inference_profile.resolve(desired, candidates) if candidates else None


def resolve_panel(
    config: dict[str, Any] | None,
    params: dict[str, Any] | None,
    registry: CliAdapterRegistry,
) -> tuple[list[str], str | None]:
    """Resolve (panel_names, judge_name) for the fusion blueprint.

    Priority for the panel: per-request ``panel`` list > per-request ``preset``
    > config ``cli_fusion.default_preset`` > all available adapters.
    """
    params = params or {}
    fusion = _fusion_config(config)
    presets = fusion.get("presets") or {}

    panel: list[str] | None = params.get(PARAM_PANEL)
    judge: str | None = params.get(PARAM_JUDGE)

    preset_name = params.get(PARAM_PRESET) or (None if panel else fusion.get("default_preset"))
    if not panel and preset_name and preset_name in presets:
        preset = presets[preset_name] or {}
        panel = preset.get("panel")
        judge = judge or preset.get("judge")

    if not panel:
        panel = registry.available() or registry.names()

    # Drop names with no configured adapter, keeping order.
    known = set(registry.names())
    panel = [n for n in panel if n in known]
    if judge and judge not in known:
        judge = None
    return panel, judge


def resolve_failover_chain(
    config: dict[str, Any] | None,
    params: dict[str, Any] | None,
    registry: CliAdapterRegistry,
) -> list[str]:
    """Ordered adapter names the single-CLI blueprint should try, in order.

    The primary is :func:`select_single_cli`. Then, unless failover is disabled:

    * an explicit ``params['fallback']`` list is appended in order, **or**
    * if no explicit list and ``params['failover']`` isn't ``False``, every other
      *installed* adapter is appended (auto-failover) so a missing/broken primary
      degrades to whatever the host actually has.

    Names are deduped (order preserved) and filtered to configured adapters.
    Returns ``[]`` when nothing is configured. Set ``failover: False`` for strict
    single-CLI behaviour (never silently switch to a different model).
    """
    params = params or {}
    primary = select_single_cli(config, params, registry)
    if not primary:
        return []
    chain = [primary]
    fallback = params.get(PARAM_FALLBACK)
    if isinstance(fallback, list):
        chain.extend(str(n) for n in fallback)
    elif params.get(PARAM_FAILOVER, True):
        chain.extend(n for n in registry.available() if n not in chain)

    known = set(registry.names())
    seen: set[str] = set()
    out: list[str] = []
    for n in chain:
        if n in known and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolve_consensus_spec(
    spec: Any, name: str | None, registry: CliAdapterRegistry
) -> tuple[list[str], str | None] | None:
    """Resolve a consensus ``spec`` into (panel_names, judge_name), or None.

    ``spec`` may be:
    * ``True`` — panel of every available CLI (real CLIs, not other designations);
    * an ``int`` N≥2 — **self-consensus**: the same persona (``name``) run N times;
    * a list — a preferred **whitelist** that falls back to the default if it
      matches nothing;
    * a dict ``{"panel": [...], "judge": "<cli>"}`` — explicit (same fallback).

    Anything falsy (``None``/``False``/``0``/``[]``) returns None (single call).
    The judge defaults to the persona when it's in the panel, else the first.
    """
    if not spec:
        return None

    known = set(registry.names())
    available = registry.available()
    available_set = set(available)

    def _non_consensus(names: list[str]) -> list[str]:
        # The default panel is real CLIs, not other consensus *designations*.
        return [n for n in names if not getattr(registry.get(n).config, "consensus", None)]

    default_panel = (
        _non_consensus(available) or _non_consensus(registry.names()) or list(available or registry.names())
    )
    judge: str | None = None

    if spec is True:
        panel = list(default_panel)
    elif isinstance(spec, int) and not isinstance(spec, bool):
        if spec < 2 or not name:
            return None  # <2 is just a single call
        panel = [name] * min(int(spec), 16)  # self-consensus: same persona, N times
    elif isinstance(spec, list):
        preferred = [n for n in spec if n in available_set]
        panel = preferred or list(default_panel)  # whitelist matched nothing -> default
    elif isinstance(spec, dict):
        wl = [n for n in (spec.get("panel") or []) if n in known]
        preferred = [n for n in wl if n in available_set] or wl
        panel = preferred or list(default_panel)
        judge = spec.get("judge") if spec.get("judge") in known else None
    else:
        return None

    if judge is None:
        judge = name if name in panel else (panel[0] if panel else None)
    return panel, judge


def resolve_agent_consensus(
    cfg, registry: CliAdapterRegistry
) -> tuple[list[str], str | None] | None:
    """Resolve the consensus panel for a configured agent (its ``cfg.consensus``)."""
    return resolve_consensus_spec(getattr(cfg, "consensus", None), getattr(cfg, "name", None), registry)


def apply_overrides(
    registry: CliAdapterRegistry, params: dict[str, Any] | None
) -> CliAdapterRegistry:
    """Apply per-request adapter overrides (currently: timeout) to a registry."""
    params = params or {}
    timeout = params.get(PARAM_TIMEOUT)
    if timeout is None:
        return registry
    patch = {name: {"timeout": float(timeout)} for name in registry.names()}
    return registry.with_overrides(patch)


# --- Chunk helpers (match what swarm.views.chat_views expects to consume) --- #

def message_chunk(content: str, *, final: bool = False, role: str = "assistant") -> dict:
    """A content-bearing chunk. ``final=True`` lets the API short-circuit."""
    chunk: dict[str, Any] = {"messages": [{"role": role, "content": content}]}
    if final:
        chunk["final"] = True
    return chunk


#: Chunk ``type`` for fusion progress side-channel events.
PROGRESS_TYPE = "fusion_progress"


def progress_chunk(content: str) -> dict:
    """A progress event on a side-channel that vanilla OpenAI clients drop.

    Deliberately carries no ``messages``/``message``/``choices`` key, so
    ``swarm.views.chat_views._extract_message_from_chunk`` returns None and the
    line never leaks into the synthesized answer. Swarm-aware UIs can render it
    by inspecting ``chunk["type"] == PROGRESS_TYPE``.
    """
    return {"type": PROGRESS_TYPE, "content": content}


def format_cli_error(adapter: CliAdapter, error: str) -> str:
    return f"[{adapter.name}] failed: {error}"
