import pytest
from unittest.mock import patch, MagicMock
from rich.syntax import Syntax
from rich.markdown import Markdown
import sys # For printing to stderr

# Assuming RICH_AVAILABLE is True for these tests. 
# If not, they'd be skipped by the decorator.
RICH_AVAILABLE = True 
try:
    # Import the specific Console that pretty_print_response will use
    from swarm.core.output_utils import pretty_print_response, RICH_AVAILABLE, Console as SwarmConsole
except ImportError:
    RICH_AVAILABLE = False # Fallback if import fails
    SwarmConsole = None # Define for static analysis if import fails

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_plain_text(monkeypatch):
    """Ensure plain text is printed directly when use_markdown is False and no code fences."""
    events = []
    class DummyConsole:
        def print(self, obj, end=None): 
            events.append(obj)
    
    monkeypatch.setattr('swarm.core.output_utils.Console', lambda *args, **kwargs: DummyConsole())
    
    messages = [{"role": "assistant", "sender": "Assistant", "content": "Hello world"}]
    pretty_print_response(messages, use_markdown=False)
    
    assert len(events) == 1, f"Expected 1 print event, got {len(events)}. Events: {events}"
    assert events[0] == "[Assistant]: Hello world", f"Unexpected event content: {events[0]}"

@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
def test_pretty_print_response_with_code_fence(monkeypatch):
    """Ensure code fences are highlighted via rich.Syntax."""
    events = []
    class DummyConsole:
        def print(self, obj, end=None): 
            events.append(obj)
            
    monkeypatch.setattr('swarm.core.output_utils.Console', lambda *args, **kwargs: DummyConsole())

    code_content = '```python\nprint("hello")\n```'
    messages = [{"role": "assistant", "sender": "Assistant", "content": code_content}]
    pretty_print_response(messages, use_markdown=False)
    
    assert any(isinstance(e, Syntax) for e in events), f"Expected Syntax in events; got {events}"
    
    syntax_event = next((e for e in events if isinstance(e, Syntax)), None)
    assert syntax_event is not None, "Syntax object not found in events"

    if syntax_event:
        assert syntax_event.code.strip() == 'print("hello")', "Syntax object code mismatch"
        
        actual_lexer_name_attr = None
        lexer_value_to_check = None

        if hasattr(syntax_event, 'language') and isinstance(getattr(syntax_event, 'language'), str):
             actual_lexer_name_attr = 'language'
             lexer_value_to_check = getattr(syntax_event, actual_lexer_name_attr)
        elif hasattr(syntax_event, 'lexer_name') and isinstance(getattr(syntax_event, 'lexer_name'), str):
             actual_lexer_name_attr = 'lexer_name'
             lexer_value_to_check = getattr(syntax_event, actual_lexer_name_attr)
        elif hasattr(syntax_event, '_lexer_name') and isinstance(getattr(syntax_event, '_lexer_name'), str): # Less ideal, but possible
             actual_lexer_name_attr = '_lexer_name'
             lexer_value_to_check = getattr(syntax_event, actual_lexer_name_attr)
        elif hasattr(syntax_event, 'lexer') and hasattr(syntax_event.lexer, 'name') and isinstance(syntax_event.lexer.name, str):
             # This case means syntax_event.lexer is an object, and its .name attribute is the string
             lexer_value_to_check = syntax_event.lexer.name
        else:
            # Fallback if no direct string attribute is found, try to get it from the lexer object if it exists
            if hasattr(syntax_event, 'lexer') and hasattr(type(syntax_event.lexer), 'name'): # Check if lexer object has a 'name' property/attribute
                 lexer_value_to_check = type(syntax_event.lexer).name # Or syntax_event.lexer.name if it's an instance var
            elif hasattr(syntax_event, 'lexer') and hasattr(type(syntax_event.lexer), 'aliases') and syntax_event.lexer.aliases:
                 lexer_value_to_check = syntax_event.lexer.aliases[0] # Pygments lexers have aliases
            else:
                 pytest.fail(f"Could not find a suitable lexer name string attribute on Syntax object. Attributes: {dir(syntax_event)}")

        assert lexer_value_to_check is not None, "Lexer name string could not be determined."
        assert lexer_value_to_check.lower() == 'python', f"Syntax object language mismatch. Expected 'python', got '{lexer_value_to_check}' (from attribute: {actual_lexer_name_attr or 'lexer.name/aliases'})"

