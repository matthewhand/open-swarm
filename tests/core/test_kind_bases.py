"""REQ-159: three kind bases are documented templates over BlueprintBase."""

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.kind_bases import (
    ALLOWED_BLUEPRINT_BASE_NAMES,
    KIND_BASE_NAMES,
    ApiKindBase,
    CliKindBase,
    KindBase,
    RemoteKindBase,
)


def test_kind_bases_subclass_blueprint_base():
    assert issubclass(ApiKindBase, BlueprintBase)
    assert issubclass(CliKindBase, BlueprintBase)
    assert issubclass(RemoteKindBase, BlueprintBase)
    assert issubclass(ApiKindBase, KindBase)


def test_kind_stamps_match_harness_types():
    assert ApiKindBase.kind == "api"
    assert CliKindBase.kind == "cli"
    assert RemoteKindBase.kind == "remote"
    assert KIND_BASE_NAMES == ("ApiKindBase", "CliKindBase", "RemoteKindBase")
    assert "BlueprintBase" in ALLOWED_BLUEPRINT_BASE_NAMES
    assert set(KIND_BASE_NAMES) <= set(ALLOWED_BLUEPRINT_BASE_NAMES)


def test_kind_bases_are_abstract_templates():
    import inspect

    assert inspect.isabstract(ApiKindBase)
    assert inspect.isabstract(CliKindBase)
    assert inspect.isabstract(RemoteKindBase)


def test_validator_accepts_api_kind_base():
    from swarm.views.agent_creator_views import BlueprintCodeValidator

    code = '''
from swarm.core.kind_bases import ApiKindBase

class DemoTeam(ApiKindBase):
    metadata = {"name": "demo", "version": "1.0.0"}

    async def run(self, messages, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "ok"}]}
'''
    result = BlueprintCodeValidator().validate_blueprint_code(code)
    assert result["valid"] is True
    assert result["structure_valid"] is True
