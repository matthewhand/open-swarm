
import pytest

from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.blueprints.rue_code.blueprint_rue_code import RueCodeBlueprint, RueSpinner


def test_rue_spinner_states():
    spinner = RueSpinner()
    spinner.start()
    states = []
    for _ in range(6):
        spinner._spin()
        states.append(spinner.current_spinner_state())
    assert states[:3] == ["Generating..", "Generating...", "Running..."]
    spinner._start_time -= 11
    assert spinner.current_spinner_state() == spinner.LONG_WAIT_MSG

def test_rue_operation_box_output(capsys):
    spinner = RueSpinner()
    spinner.start()
    display_operation_box(
        title="Rue Test",
        content="Testing operation box",
        spinner_state=spinner.current_spinner_state(),
        emoji="📝"
    )
    captured = capsys.readouterr()
    assert "Rue Test" in captured.out
    assert "Testing operation box" in captured.out
    assert "📝" in captured.out

@pytest.mark.asyncio
async def test_rue_run_box(monkeypatch, capsys):
    class DummyLLM:
        def chat_completion_stream(self, messages, **_):
            class DummyStream:
                def __aiter__(self): return self
                async def __anext__(self):
                    raise StopAsyncIteration
            return DummyStream()
    blueprint = RueCodeBlueprint(blueprint_id="test_rue")
    blueprint.llm = DummyLLM()
    monkeypatch.setattr(blueprint, "render_prompt", lambda *a, **k: "prompt")
    out = []
    async for msg in blueprint.run([{"role": "user", "content": "test"}]):
        out.append(msg)
    captured = capsys.readouterr()
    assert "RueCode Code Results" in captured.out
    assert "RueCode Semantic Results" in captured.out
    assert "RueCode Summary" in captured.out
    assert out

# Edge case: empty user message
@pytest.mark.asyncio
async def test_rue_run_empty(monkeypatch, capsys):
    blueprint = RueCodeBlueprint(blueprint_id="test_rue")
    out = []
    async for msg in blueprint.run([{"role": "assistant", "content": "no user"}]):
        out.append(msg)
    captured = capsys.readouterr()
    assert "RueCode Error" in captured.out
    assert out
