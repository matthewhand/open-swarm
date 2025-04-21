import pytest
from swarm.core.output_utils import pretty_print_response, RICH_AVAILABLE
from rich.syntax import Syntax

def test_pretty_print_response_plain_text(capsys):
    """Ensure plain assistant text prints correctly without code fences."""
    messages = [
        {"role": "assistant", "sender": "Assistant", "content": "Hello, world!"}
    ]
    pretty_print_response(messages, use_markdown=False)
    captured = capsys.readouterr()
    assert "Assistant:" in captured.out
    assert "Hello, world!" in captured.out

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_with_code_fence(monkeypatch):
    """Ensure code fences are highlighted via rich.Syntax."""
    # Dummy Console to capture print calls
    class DummyConsole:
        def __init__(self):
            self.events = []
        def print(self, obj):
            self.events.append(obj)
    dummy_console = DummyConsole()
    # Patch rich.console.Console to always return our dummy_console instance
    import rich.console
    monkeypatch.setattr(rich.console, 'Console', lambda *args, **kwargs: dummy_console)

    code = '```python\nprint("hello")\n```'
    messages = [{"role": "assistant", "sender": "Assistant", "content": code}]
    pretty_print_response(messages, use_markdown=False, _console=dummy_console)
    # Expect at least one Syntax object
    assert any(isinstance(e, Syntax) for e in dummy_console.events), f"Expected Syntax in events; got {dummy_console.events}"