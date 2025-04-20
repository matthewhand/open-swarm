from swarm.ux.ansi_box import ansi_box

def test_ansi_box_basic(capsys):
    ansi_box('Searched filesystem', 'Found 12 files', count=12, params={'pattern': '*.py'}, style='success', emoji='💾')
    out = capsys.readouterr().out
    assert 'Searched filesystem' in out
    assert 'Results: 12' in out
    assert 'pattern' in out
    assert '💾' in out

def test_ansi_box_multiline(capsys):
    ansi_box('Analyzed code', ['Line 1', 'Line 2', 'Line 3'], style='default', emoji='🧑‍💻')
    out = capsys.readouterr().out
    assert 'Analyzed code' in out
    assert 'Line 2' in out
    assert '🧑‍💻' in out
