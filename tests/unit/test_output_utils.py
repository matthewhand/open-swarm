import pytest
from swarm.core.output_utils import pretty_print_response, RICH_AVAILABLE
from rich.syntax import Syntax
import re

def test_pretty_print_response_plain_text(capsys):
    """Ensure plain assistant text prints correctly without code fences."""
    import re
    messages = [
        {"role": "assistant", "sender": "Assistant", "content": "Hello, world!"}
    ]
    pretty_print_response(messages, use_markdown=False)
    captured = capsys.readouterr()
    # Strip ANSI escape codes for robust assertion
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean_out = ansi_escape.sub('', captured.out)
    assert "[Assistant]:" in clean_out or "Assistant:" in clean_out
    assert "Hello, world!" in clean_out

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_with_code_fence(monkeypatch):
    """Ensure code fences are highlighted via rich.Syntax."""
    events = []
    # Dummy Console to capture print calls
    class DummyConsole:
        def print(self, obj):
            events.append(obj)
    # Patch rich.console.Console
    import rich.console
    monkeypatch.setattr(rich.console, 'Console', lambda *args, **kwargs: DummyConsole())

    code = '```python\nprint("hello")\n```'
    messages = [{"role": "assistant", "sender": "Assistant", "content": code}]
    pretty_print_response(messages, use_markdown=False)
    # Expect at least one Syntax object
    assert any(isinstance(e, Syntax) for e in events), f"Expected Syntax in events; got {events}"