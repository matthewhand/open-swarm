"""Integration tests for the fs_introspect blueprint grammar + dispatch."""
from __future__ import annotations

import pytest

from swarm.blueprints.fs_introspect.blueprint_fs_introspect import FsIntrospectBlueprint


async def _collect(gen):
    return [c async for c in gen]


def _final(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


@pytest.fixture
def bp(tmp_path):
    (tmp_path / "swarm_config.json").write_text('{\n  "llm": {},\n  "cli_agents": {}\n}', encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "notes.txt").write_text("alpha\nbravo\ncharlie", encoding="utf-8")
    (tmp_path / "log.txt").write_text("\n".join(f"line{i}" for i in range(1, 9)), encoding="utf-8")
    config = {"filesystem": {"permission": "readonly", "allowed_paths": [str(tmp_path)]}}
    b = FsIntrospectBlueprint(config=config)
    b._tmp = tmp_path  # type: ignore[attr-defined]
    return b


async def _ask(bp, content, params=None):
    bp.set_params(params or {})
    return _final(await _collect(bp.run([{"role": "user", "content": content}])))


@pytest.mark.asyncio
async def test_read(bp):
    out = await _ask(bp, f"read {bp._tmp / 'swarm_config.json'}")
    assert '"cli_agents"' in out


@pytest.mark.asyncio
async def test_bare_path_reads_file(bp):
    out = await _ask(bp, str(bp._tmp / "swarm_config.json"))
    assert '"llm"' in out


@pytest.mark.asyncio
async def test_bare_path_lists_dir(bp):
    out = await _ask(bp, str(bp._tmp))
    assert "swarm_config.json" in out and "sub" in out


@pytest.mark.asyncio
async def test_grep(bp):
    out = await _ask(bp, f"grep bravo {bp._tmp / 'sub'}")
    assert "notes.txt:2: bravo" in out


@pytest.mark.asyncio
async def test_find(bp):
    out = await _ask(bp, f"find *.txt in {bp._tmp}")
    assert "notes.txt" in out and "log.txt" in out


@pytest.mark.asyncio
async def test_head_and_tail(bp):
    head = await _ask(bp, f"head {bp._tmp / 'log.txt'} 2")
    assert head == "1: line1\n2: line2"
    tail = await _ask(bp, f"tail {bp._tmp / 'log.txt'} 2")
    assert tail == "7: line7\n8: line8"


@pytest.mark.asyncio
async def test_stat_via_params(bp):
    out = await _ask(bp, "x", params={"op": "stat", "path": str(bp._tmp / "log.txt")})
    assert "type: file" in out


@pytest.mark.asyncio
async def test_read_line_range_via_params(bp):
    out = await _ask(bp, "x", params={"op": "read", "path": str(bp._tmp / "log.txt"), "start_line": 2, "end_line": 3})
    assert out == "2: line2\n3: line3"


@pytest.mark.asyncio
async def test_blocked_path(bp):
    out = await _ask(bp, "read /etc/passwd")
    assert "filesystem error" in out and "outside the allowed roots" in out


@pytest.mark.asyncio
async def test_usage_when_empty(bp):
    out = await _ask(bp, "")
    assert "Usage" in out
