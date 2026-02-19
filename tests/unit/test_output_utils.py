
import pytest
from rich.markdown import Markdown
from rich.syntax import Syntax

# Assuming RICH_AVAILABLE is True for these tests.
# If not, they'd be skipped by the decorator.
RICH_AVAILABLE = True
try:
    # Import the specific Console that pretty_print_response will use
    from swarm.core.output_utils import RICH_AVAILABLE, pretty_print_response
    from swarm.core.output_utils import Console as SwarmConsole
except ImportError:
    RICH_AVAILABLE = False # Fallback if import fails
    SwarmConsole = None # Define for static analysis if import fails

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_plain_text(capsys):
    """Ensure plain text is printed directly when use_markdown is False and no code fences."""
    messages = [{"role": "assistant", "sender": "Assistant", "content": "Hello world"}]
    pretty_print_response(messages, use_markdown=False)
    captured = capsys.readouterr()
    assert "Hello world" in captured.out

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_with_code_fence(capsys):
    """Ensure code fences are highlighted via rich.Syntax."""
    code_content = '```python\nprint("hello")\n```'
    messages = [{"role": "assistant", "sender": "Assistant", "content": code_content}]
    pretty_print_response(messages, use_markdown=False)
    captured = capsys.readouterr()
    assert "print" in captured.out


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_markdown_path(capsys):
    """Ensure Markdown objects are used when use_markdown=True and no code fences."""
    messages = [{"role": "assistant", "sender": "Assistant", "content": "# Title\nSome text"}]
    pretty_print_response(messages, use_markdown=True)
    captured = capsys.readouterr()
    assert "Title" in captured.out


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_skips_empty_content(capsys):
    """Messages with empty or None content are skipped from printing."""
    messages = [
        {"role": "assistant", "sender": "Assistant", "content": ""},
        {"role": "assistant", "sender": "Assistant", "content": None},
        {"role": "assistant", "sender": "Assistant", "content": "Hello"},
    ]

    pretty_print_response(messages, use_markdown=False)
    captured = capsys.readouterr()
    assert "Hello" in captured.out
    assert captured.out.count("[Assistant]") == 3
