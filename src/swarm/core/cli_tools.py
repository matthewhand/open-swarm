"""Expose CLI adapters and consensus as agent tools.

The composable layer over :mod:`swarm.core.consensus` and
:mod:`swarm.core.cli_adapter`: turn a CLI persona or a whole consensus panel into
something an openai-agents ``Agent`` can call mid-reasoning. This is what makes
fusion *granular* — an orchestrating agent runs a single inference and reaches
for ``consensus(...)`` only on the hard sub-question, instead of fanning out on
everything.

Each factory returns a plain ``async`` callable (directly awaitable and testable);
wrap it with :func:`as_function_tool` to hand it to an ``Agent(tools=[...])``.
"""

from __future__ import annotations

import re
from typing import Awaitable, Callable

from swarm.core.cli_adapter import CliAdapter
from swarm.core.consensus import run_consensus

try:  # openai-agents is a core dep, but keep import failures non-fatal for tooling
    from agents import function_tool
except Exception:  # pragma: no cover
    function_tool = None  # type: ignore[assignment]

_SLUG_RE = re.compile(r"[^A-Za-z0-9_]+")


def _ident(name: str) -> str:
    """A safe Python identifier fragment for a tool name."""
    return _SLUG_RE.sub("_", name).strip("_") or "cli"


def cli_persona(adapter: CliAdapter) -> Callable[[str], Awaitable[str]]:
    """An async callable that asks one CLI a question and returns its answer.

    On failure it returns a short ``[<name> unavailable: …]`` note rather than
    raising, so an orchestrating agent can react instead of crashing.
    """

    async def ask(question: str) -> str:
        res = await adapter.run(question)
        return res.text if res.ok else f"[{adapter.name} unavailable: {res.error}]"

    ask.__name__ = f"ask_{_ident(adapter.name)}"
    ask.__doc__ = f"Ask the '{adapter.name}' CLI agent a question and return its answer."
    return ask


def consensus_fn(
    panel: list[CliAdapter], judge: CliAdapter | None = None
) -> Callable[[str], Awaitable[str]]:
    """An async callable that runs a consensus panel and returns the agreed answer.

    Returns the synthesized consensus, or ``(no consensus reached)`` if every
    panelist failed.
    """

    async def consensus(question: str) -> str:
        res = await run_consensus(question, panel, judge)
        return res.answer or "(no consensus reached)"

    consensus.__doc__ = (
        "Get a cross-model consensus answer to a high-stakes question: a panel of "
        "independent CLI agents deliberate and a judge synthesizes their agreement."
    )
    return consensus


def as_function_tool(
    fn: Callable[..., Awaitable[str]], *, name: str | None = None, description: str | None = None
):
    """Wrap an async callable as an openai-agents ``FunctionTool``.

    Raises if openai-agents is unavailable. The callable's name/docstring become
    the tool's name/description unless overridden.
    """
    if function_tool is None:  # pragma: no cover
        raise RuntimeError("openai-agents is not installed; cannot build a function tool")
    if name:
        fn.__name__ = name
    if description:
        fn.__doc__ = description
    return function_tool(fn)
