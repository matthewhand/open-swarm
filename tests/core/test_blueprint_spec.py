"""Published blueprint interface is valid Python and matches the creator contract."""

from swarm.core.blueprint_spec import (
    BLUEPRINT_AGENT_BRIEF,
    BLUEPRINT_INTERFACE,
    BLUEPRINT_ONE_LINER,
)


def test_interface_is_parseable_python():
    import ast

    ast.parse(BLUEPRINT_INTERFACE)


def test_interface_names_the_contract():
    assert "class MyTeamBlueprint(BlueprintBase)" in BLUEPRINT_INTERFACE
    assert "async def run(self, messages, **kwargs)" in BLUEPRINT_INTERFACE
    assert '"messages"' in BLUEPRINT_INTERFACE
    assert "BlueprintBase" in BLUEPRINT_AGENT_BRIEF
    assert "coded agent team" in BLUEPRINT_ONE_LINER
