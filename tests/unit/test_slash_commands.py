import pytest

from swarm.core.slash_commands import slash_registry


def test_compact_accepts_through_message_id_arg():
    captured = {}

    class DummyBP:
        blueprint_name = "jeeves"

    def fake_compact_backlog(**kwargs):
        captured.update(kwargs)

        class Row:
            body = "digest"

        return Row(), []

    import swarm.core.chat_compact as compact_mod

    original = compact_mod.compact_backlog
    compact_mod.compact_backlog = fake_compact_backlog
    try:
        out = slash_registry.get("/compact")(
            DummyBP(),
            "12",
            conversation_id="c1",
            messages=[{"role": "user", "content": "hi"}],
            user=object(),
        )
    finally:
        compact_mod.compact_backlog = original
    assert out == "digest"
    assert captured["through_message_id"] == "12"


def test_help_and_compact_registered():
    help_fn = slash_registry.get('/help')
    compact_fn = slash_registry.get('/compact')
    assert callable(help_fn)
    assert callable(compact_fn)
def test_model_command_list_and_set():
    # Create dummy blueprint with some profiles
    class DummyBP:
        def __init__(self):
            self.config = {'llm': {'default': {}, 'gpt-mock': {}, 'gpt-4': {}}}
            self._session_model_profile = 'default'
            self._agent_model_overrides = {}
    bp = DummyBP()
    model_fn = slash_registry.get('/model')
    # List current
    out = model_fn(bp, None)
    assert isinstance(out, list)
    assert any('session default: default' in line.lower() for line in out)
    # Set session default
    res = model_fn(bp, 'gpt-4')
    assert "session default llm profile set to 'gpt-4'" in res.lower()
    assert bp._session_model_profile == 'gpt-4'
    # Override specific agent
    res2 = model_fn(bp, 'Planner gpt-mock')
    assert "agent 'planner'" in res2.lower()
    assert bp._agent_model_overrides.get('Planner') == 'gpt-mock'
    # List now includes override
    out2 = model_fn(bp, None)
    assert any('agent planner: gpt-mock' in line.lower() for line in out2)
@pytest.mark.parametrize("cmd, expect", [
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
