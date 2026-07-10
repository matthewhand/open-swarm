"""Grok as first-class live MoA participant (no Codex)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from swarm.core.moa import GrokParticipantBackend, MoAOrchestrator, PermissionMode
from swarm.core.moa.backends import GrokParticipantBackend as GrokFromBackends
from swarm.core.moa.cli import build_backend
from swarm.blueprints.moa.blueprint_moa import MoABlueprint


def test_grok_exported_from_package_and_backends():
    assert GrokParticipantBackend is GrokFromBackends


def test_grok_build_command_is_readonly_and_not_codex():
    be = GrokParticipantBackend(grok_bin="/usr/bin/grok")
    argv = be.build_command("review auth", cwd="/repo")
    assert argv[0] == "/usr/bin/grok"
    assert "-p" in argv
    tools = argv[argv.index("--disallowed-tools") + 1]
    assert "Write" in tools and "Edit" in tools
    assert "--approve-all" not in argv
    assert "codex" not in " ".join(argv).lower()
    assert "--cwd" in argv and "/repo" in argv


def test_build_backend_prefers_fake_default_and_grok():
    fake = build_backend(backend="fake", fake_responses={"a": "x"})
    assert type(fake).__name__ == "FakeParticipantBackend"
    grok = build_backend(backend="grok", timeout=10)
    assert isinstance(grok, GrokParticipantBackend)
    with pytest.raises(ValueError, match="unknown backend"):
        build_backend(backend="codex")


@pytest.mark.asyncio
async def test_multi_seat_grok_records_separate_consults():
    """Multiple seat labels → multiple one-shots with seat framing."""
    be = GrokParticipantBackend(grok_bin="grok")

    async def fake_exec(*argv, **kwargs):
        class Proc:
            returncode = 0

            async def communicate(self):
                # last prompt arg is after -p
                return (b"opinion text", b"")

            def kill(self):
                pass

            async def wait(self):
                return 0

        return Proc()

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=fake_exec)):
        orch = MoAOrchestrator(backend=be)
        result = await orch.run(
            "Should we rate-limit?",
            participants=["analyst", "critic"],
        )
    assert len(be.calls) == 2
    assert {c["agent"] for c in be.calls} == {"analyst", "critic"}
    assert all(c["permission"] == PermissionMode.APPROVE_READS.value for c in be.calls)
    assert all("[MoA seat:" in c["prompt"] for c in be.calls)
    assert result.determination is not None
    assert set(result.determination.participant_names) == {"analyst", "critic"}


@pytest.mark.asyncio
async def test_blueprint_backend_grok_wiring():
    bp = MoABlueprint(blueprint_id="moa")
    bp._config = {"moa": {"backend": "grok", "participants": ["grok"]}}
    bp.set_params({})
    backend = bp._backend()
    assert isinstance(backend, GrokParticipantBackend)
    assert bp._participants() == ["grok"]


@pytest.mark.asyncio
async def test_blueprint_fake_default_no_codex_in_seats():
    bp = MoABlueprint(blueprint_id="moa")
    bp._config = {}
    bp.set_params(
        {
            "backend": "fake",
            "fake_responses": {
                "analyst": '{"claim":"yes","confidence":0.9}',
                "critic": '{"claim":"yes with tests","confidence":0.8}',
            },
            "participants": ["analyst", "critic"],
        }
    )
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Ship?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert "messages" in final
    names = final["meta"]["backends"]
    assert "codex" not in names
    assert set(names) == {"analyst", "critic"}
