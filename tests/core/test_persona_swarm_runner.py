"""Model B Runner path: prove live hook invokes Runner when available."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from swarm.core.persona_swarm import run_persona_swarm_with_runner


@pytest.mark.asyncio
async def test_runner_path_invokes_agents_runner(tmp_path: Path):
    """When Runner.run succeeds, we use the live path (not only scripted fallback)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "notes.txt").write_text("payload", encoding="utf-8")

    fake_result = SimpleNamespace(final_output="Runner produced this answer")

    with patch("agents.Runner.run", new=AsyncMock(return_value=fake_result)) as mock_run:
        result = await run_persona_swarm_with_runner(
            ws,
            "Coordinate researcher and implementer on notes.txt",
            seed_files=None,
        )
        mock_run.assert_awaited()
        assert result.steps
        assert result.steps[0].persona == "coordinator"
        assert "Runner produced" in result.final
        assert result.steps[0].ok
        assert any("path=runner" in t for t in result.steps[0].tool_trace)


@pytest.mark.asyncio
async def test_runner_path_fallback_on_runner_error(tmp_path: Path):
    """Runner failure falls back to scripted R/W persona switch."""
    with patch(
        "agents.Runner.run",
        new=AsyncMock(side_effect=RuntimeError("no API key")),
    ):
        result = await run_persona_swarm_with_runner(
            tmp_path / "fb",
            "Summarize and write summary.md",
            seed_files={"notes.txt": "edge rate limit\n"},
        )
    assert (tmp_path / "fb" / "summary.md").is_file() or result.writes
    assert result.agents.get("implementer") == "Implementer"
