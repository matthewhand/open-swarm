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
    default = _fusion_config(config).get("default_cli")
    if default:
        return default
    available = registry.available()
    if available:
        return available[0]
    names = registry.names()
    return names[0] if names else None


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


def progress_text(chunk: dict) -> str | None:
    """Return the text of a progress chunk, or None if it isn't one."""
    if isinstance(chunk, dict) and chunk.get("type") == PROGRESS_TYPE:
        return chunk.get("content")
    return None


def format_cli_error(adapter: CliAdapter, error: str) -> str:
    return f"[{adapter.name}] failed: {error}"
