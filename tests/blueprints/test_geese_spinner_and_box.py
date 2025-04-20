import pytest
import time
from src.swarm.blueprints.common.operation_box_utils import display_operation_box
import sys
import io
from src.swarm.blueprints.geese import blueprint_geese as geese_mod
from unittest.mock import patch

# Geese spinner states (mimic other blueprints)
SPINNER_STATES = ["Generating.", "Generating..", "Generating...", "Running..."]
LONG_WAIT_MSG = "Generating... Taking longer than expected"

class GeeseSpinner:
    def __init__(self):
        self._idx = 0
        self._start_time = None
        self._last_frame = SPINNER_STATES[0]
    def start(self):
        self._start_time = time.time()
        self._idx = 0
        self._last_frame = SPINNER_STATES[0]
    def _spin(self):
        self._idx = (self._idx + 1) % len(SPINNER_STATES)
        self._last_frame = SPINNER_STATES[self._idx]
    def current_spinner_state(self):
        if self._start_time and (time.time() - self._start_time) > 10:
            return LONG_WAIT_MSG
        return self._last_frame

def test_geese_spinner_states():
    spinner = GeeseSpinner()
    spinner.start()
    states = []
    for _ in range(6):
        spinner._spin()
        states.append(spinner.current_spinner_state())
    assert states[:3] == ["Generating..", "Generating...", "Running..."]
    spinner._start_time -= 11
    assert spinner.current_spinner_state() == LONG_WAIT_MSG

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
def test_progressive_demo_operation_box(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    class DummyNotifier:
        def print_box(self, *args, **kwargs):
            pass
    blueprint.notifier = DummyNotifier()
    display_calls = []
    # Patch display_operation_box in BOTH the utility module and the geese blueprint module
    import src.swarm.blueprints.common.operation_box_utils as opbox_utils
    import src.swarm.blueprints.geese.blueprint_geese as geese_mod
    orig_display = opbox_utils.display_operation_box
    def record_display(*args, **kwargs):
        display_calls.append((args, kwargs))
        return orig_display(*args, **kwargs)
    opbox_utils.display_operation_box = record_display
    geese_mod.display_operation_box = record_display
    try:
        async def run_and_collect():
            results = []
            async for r in blueprint.run([{"role": "user", "content": "demo progressive"}]):
                results.append(r)
            return results
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(run_and_collect())
    finally:
        opbox_utils.display_operation_box = orig_display
        geese_mod.display_operation_box = orig_display
    # Should have 5 progressive updates
    assert len(display_calls) == 5
    # Each call should increment result_count and progress_line
    for i, (args, kwargs) in enumerate(display_calls, 1):
        assert kwargs["title"] is not None
        assert kwargs["content"] is not None
        assert kwargs["result_count"] == i
        assert kwargs["progress_line"] == i
        assert kwargs["total_lines"] == 5
        assert kwargs.get("op_type", "search") == "search"
    # Final yield should indicate completion
    assert any("progress" in str(r).lower() for r in results)
