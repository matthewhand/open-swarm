from swarm.ux.ansi_box import ansi_box


def test_header_without_params_or_results(capsys):
    """Header should not include Params or Results when not provided."""
    ansi_box('Analyze', 'Done', count=None, params=None, style='default', emoji=None)
    out = capsys.readouterr().out
    # Title must be present, but not the phrases
    assert 'Analyze' in out
    assert 'Results:' not in out
    assert 'Params:' not in out


def test_list_content_and_newlines(capsys):
    """List content and embedded newlines are printed line-by-line."""
    content = [
        'Line A',
        'Block B\nLine B2',
        'Line C',
    ]
    ansi_box('Multiline', content, style='success', emoji='🧪')
    out = capsys.readouterr().out
    assert 'Multiline' in out
    assert '🧪' in out
    assert 'Line A' in out
    assert 'Block B' in out
    assert 'Line B2' in out
    assert 'Line C' in out

