

def test_pretty_print_response_mixed_text_code_markdown(monkeypatch):
    """Verify behavior for text before/after a code block with markdown enabled."""
    events = []

    class DummyConsole:
        def print(self, obj, end=None):
            events.append(obj)

    # Patch Console constructor in module under test to return our dummy
    monkeypatch.setattr(
        'swarm.core.output_utils.Console',
        lambda *args, **kwargs: DummyConsole(),
        raising=True,
    )

    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from swarm.core.output_utils import pretty_print_response

    content = (
        "Intro text before.\n\n"
        "```python\nprint('hello')\n```"  # code block
        "\n\nAnd some markdown after with **bold**."
    )
    messages = [{"role": "assistant", "sender": "Assistant", "content": content}]

    pretty_print_response(messages, use_markdown=True)

    # Expectations: prefix printed (string), Syntax object printed, then Markdown object printed
    assert any(isinstance(e, str) and e.startswith("[Assistant]: ") for e in events), (
        f"Expected a prefix string, saw: {events}"
    )
    assert any(isinstance(e, Syntax) for e in events), "Expected a Syntax render for code fence"
    assert any(isinstance(e, Markdown) for e in events), "Expected Markdown for trailing text"


def test_pretty_print_response_plain_text_when_rich_disabled(monkeypatch):
    """If RICH_AVAILABLE is False, function should fall back to plain text printing."""
    events = []

    class DummyConsole:
        def print(self, obj, end=None):
            events.append(obj)

    import swarm.core.output_utils as ou

    # Force rich disabled path within the already-imported module
    monkeypatch.setattr(ou, 'RICH_AVAILABLE', False, raising=False)
    monkeypatch.setattr(ou, 'Console', lambda *args, **kwargs: DummyConsole(), raising=True)

    messages = [{"role": "assistant", "sender": "Assistant", "content": "Hello from plain"}]
    ou.pretty_print_response(messages, use_markdown=True)

    # Only plain string output expected (no Markdown/Syntax objects)
    assert any(isinstance(e, str) and e.endswith("Hello from plain") for e in events), events
    assert not any(getattr(e, '__class__', None).__name__ in {"Syntax", "Markdown"} for e in events)
