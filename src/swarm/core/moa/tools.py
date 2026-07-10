"""Orchestrator-facing helpers: ``consult_moa`` as a callable tool surface.

Agents / blueprints that own writes can call this to gather read-only opinions
without giving participants any write capability.
"""

from __future__ import annotations

from typing import Any

from swarm.core.moa.cli import build_backend, run_moa_cli
from swarm.core.moa.types import PermissionMode


async def consult_moa(
    question: str,
    participants: list[str] | None = None,
    *,
    backend: str = "fake",
    fake_responses: dict[str, str] | None = None,
    cwd: str | None = None,
    permission: str = PermissionMode.APPROVE_READS.value,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Collect read-only opinions and return orchestrator determination (no act).

    Designed as the single entry an orchestrator agent should use for MoA.
    Never performs writes; call a separate act path if impact is required.
    """
    names = list(participants or (["grok"] if backend == "grok" else ["analyst", "critic"]))
    if backend == "fake" and not fake_responses:
        fake_responses = {
            n: f"(stub opinion from {n} — provide fake_responses or use backend=grok)"
            for n in names
        }
    # Validate backend early (raises on unknown names).
    build_backend(
        backend=backend,
        fake_responses=fake_responses if backend == "fake" else None,
        timeout=timeout,
    )
    return await run_moa_cli(
        question,
        names,
        backend=backend,
        fake_responses=fake_responses,
        cwd=cwd,
        permission=permission,
        timeout=timeout,
        act=False,
    )
