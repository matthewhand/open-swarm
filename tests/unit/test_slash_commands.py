import pytest
from swarm.core.slash_commands import slash_registry

def test_help_and_compact_registered():
    help_fn = slash_registry.get('/help')
    compact_fn = slash_registry.get('/compact')
    assert callable(help_fn)
    assert callable(compact_fn)
@pytest.mark.parametrize("cmd, expect", [
    ('/model', 'model'),
    ('/approval', 'approval'),
    ('/history', 'history'),
    ('/clear', 'cleared'),
    ('/clearhistory', 'cleared'),
])
def test_additional_slash_commands(cmd, expect):
    fn = slash_registry.get(cmd)
    assert callable(fn), f"{cmd} should be registered"
    # pass args for /model, none for others
    out = fn(None, 'testarg') if cmd == '/model' else fn(None)
    assert isinstance(out, str)
    assert expect in out.lower(), f"Expected '{expect}' in output of {cmd}, got: {out}"