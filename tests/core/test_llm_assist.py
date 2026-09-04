from swarm.core.llm_assist import (
    extract_python,
    fallback_quickstarts,
    generate_blueprint_class,
    generate_quickstarts,
    parse_quickstarts_payload,
)


def test_fallback_quickstarts_use_agent_name():
    items = fallback_quickstarts("Coder")
    assert len(items) == 4
    assert items[0]["label"] == "Explain Coder"
    assert "Hermes" in items[3]["prompt"]


def test_parse_quickstarts_json_object():
    raw = """{
      "quickstarts": [
        {"key": "A", "label": "Explain Bot", "prompt": "Who are you?"},
        {"key": "B", "label": "Customise Bot", "prompt": "Tune me"},
        {"key": "C", "label": "Install CLI", "prompt": "Need grok?"},
        {"key": "D", "label": "Connect remote", "prompt": "Hermes?"}
      ]
    }"""
    items = parse_quickstarts_payload(raw, name="Bot")
    assert [i["label"] for i in items] == [
        "Explain Bot",
        "Customise Bot",
        "Install CLI",
        "Connect remote",
    ]


def test_parse_quickstarts_falls_back_when_junk():
    items = parse_quickstarts_payload("<unused50>not json", name="Analyst")
    assert items[0]["label"] == "Explain Analyst"


def test_generate_quickstarts_skips_llm_under_pytest():
    items = generate_quickstarts("Writer", "You write clearly.")
    assert items[0]["label"] == "Explain Writer"


def test_generate_blueprint_class_skips_llm_under_pytest():
    assert generate_blueprint_class(name="X", description="d", requirements="do stuff") is None


def test_extract_python_from_fence():
    text = "Sure:\n```python\nclass Foo(BlueprintBase):\n    pass\n```\n"
    assert "class Foo(BlueprintBase)" in extract_python(text)


def test_validator_accepts_published_interface():
    from swarm.core.blueprint_spec import BLUEPRINT_INTERFACE
    from swarm.views.agent_creator_views import BlueprintCodeValidator

    result = BlueprintCodeValidator().validate_blueprint_code(BLUEPRINT_INTERFACE)
    assert result["syntax_valid"] is True
    assert result["structure_valid"] is True
    assert result["valid"] is True
    assert not any("AsyncGenerator" in e for e in result["errors"])
    assert not any("Any" in e for e in result["errors"])


def test_validator_accepts_annotated_metadata():
    from swarm.views.agent_creator_views import BlueprintCodeValidator

    code = '''
from swarm.core.blueprint_base import BlueprintBase
from typing import Any, ClassVar

class AnnBlueprint(BlueprintBase):
    metadata: ClassVar[dict[str, Any]] = {"name": "ann", "version": "1.0.0"}

    async def run(self, messages, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "ok"}]}
'''
    result = BlueprintCodeValidator().validate_blueprint_code(code)
    assert result["valid"] is True
    assert not any("metadata" in w.lower() for w in result["warnings"])
