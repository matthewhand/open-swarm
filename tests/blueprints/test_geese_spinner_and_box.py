"""Spinner and operation-box UX tests for the Geese blueprint.

Ported from archive/local-main-2025-04 and adapted to current main:
- imports use the installed ``swarm`` package (not ``src.swarm``),
- the archive's hand-rolled GeeseSpinner mock class test was dropped in
  favour of asserting the real SpinnerState enum used by the blueprint,
- the progressive-output test asserts one display_operation_box call per
  SpinnerState member (main's test-mode demo), instead of a hardcoded 5.
"""
import io
import sys

import pytest

import swarm.blueprints.common.operation_box_utils as opbox_utils
import swarm.blueprints.geese.blueprint_geese as geese_mod
from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.blueprints.geese.blueprint_geese import SpinnerState

LONG_WAIT_MSG = "Generating... Taking longer than expected"


def test_geese_spinner_states_enum():
    values = [state.value for state in SpinnerState]
    assert values[:4] == ["Generating.", "Generating..", "Generating...", "Running..."]
    assert SpinnerState.LONG_WAIT.value == LONG_WAIT_MSG


def test_display_operation_box_basic(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Test Title",
        content="Test Content",
        result_count=5,
        params={'query': 'foo'},
        progress_line=10,
        total_lines=100,
        spinner_state="Generating...",
        emoji="🔍"
    )
    out = buf.getvalue()
    assert "Test Content" in out
    assert "Progress: 10/100" in out
    assert "Results: 5" in out
    assert "Query: foo" in out
    assert "Generating..." in out
    assert "🔍" in out


def test_display_operation_box_default_emoji(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Test Title",
        content="Test Content"
    )
    out = buf.getvalue()
    assert "Test Content" in out
    assert "💡" in out


@pytest.fixture
def geese_blueprint_instance():
    GeeseBlueprint = geese_mod.GeeseBlueprint
    config = {
        "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
        "settings": {"default_llm_profile": "default", "default_markdown_output": True},
        "blueprints": {},
        "llm_profile": "default",
        "mcpServers": {}
    }
    instance = GeeseBlueprint("test_geese", config=config)
    instance.debug = True
    return instance


@pytest.mark.asyncio
async def test_progressive_demo_operation_box(geese_blueprint_instance, monkeypatch):
    blueprint = geese_blueprint_instance
    display_calls = []
    orig_display = opbox_utils.display_operation_box

    def record_display(*args, **kwargs):
        display_calls.append((args, kwargs))
        return orig_display(*args, **kwargs)

    # Patch display_operation_box in BOTH the utility module and the geese
    # blueprint module (geese imports it at module level).
    monkeypatch.setattr(opbox_utils, "display_operation_box", record_display)
    monkeypatch.setattr(geese_mod, "display_operation_box", record_display)

    results = []
    async for r in blueprint.run([{"role": "user", "content": "demo progressive"}]):
        results.append(r)

    # One progressive update per SpinnerState member
    total = len(list(SpinnerState))
    assert len(display_calls) == total
    # Each call should increment result_count and progress_line
    for i, (args, kwargs) in enumerate(display_calls, 1):
        assert kwargs["title"] is not None
        assert kwargs["content"] is not None
        assert kwargs["result_count"] == i
        assert kwargs["progress_line"] == i
        assert kwargs["total_lines"] == total
        assert kwargs.get("op_type", "search") == "search"
    # Run should report progress along the way
    assert any("progress" in str(r).lower() for r in results)
