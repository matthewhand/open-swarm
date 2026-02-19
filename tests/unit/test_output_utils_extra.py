

def test_pretty_print_response_mixed_text_code_markdown(capsys):
    """Verify behavior for text before/after a code block with markdown enabled."""
    from swarm.core.output_utils import pretty_print_response

    content = (
        "Intro text before.\n\n"
        "```python\nprint('hello')\n```"  # code block
        "\n\nAnd some markdown after with **bold**."
    )
    messages = [{"role": "assistant", "sender": "Assistant", "content": content}]

    pretty_print_response(messages, use_markdown=True)

    captured = capsys.readouterr()
    assert "Intro text before" in captured.out
    assert "print('hello')" in captured.out
    assert "bold" in captured.out


def test_pretty_print_response_plain_text_when_rich_disabled(capsys):
    """If RICH_AVAILABLE is False, function should fall back to plain text printing."""
    import swarm.core.output_utils as ou

    # Force rich disabled path within the already-imported module
    original_rich_available = ou.RICH_AVAILABLE
    ou.RICH_AVAILABLE = False

    messages = [{"role": "assistant", "sender": "Assistant", "content": "Hello from plain"}]
    ou.pretty_print_response(messages, use_markdown=True)

    captured = capsys.readouterr()
    assert "Hello from plain" in captured.out

    # Restore original value
    ou.RICH_AVAILABLE = original_rich_available
