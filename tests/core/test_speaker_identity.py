"""REQ-70 speaker identity: named assistant vs delimiter wrap."""

from swarm.core.speaker_identity import (
    ADAPTER_NAME_FIELD,
    SPEAKER_CLOSE,
    SPEAKER_END,
    SPEAKER_OPEN,
    adapter_id_for_blueprint,
    apply_speaker_identity,
    speaker_path_for,
    unwrap_speaker,
    wrap_speaker,
)


def test_adapter_table_covers_shipped_paths():
    assert ADAPTER_NAME_FIELD["openai_compat"]["path"] == "named"
    assert ADAPTER_NAME_FIELD["openai_compat"]["name_field"] == "accepted"
    for key in (
        "cli:grok",
        "cli:agy",
        "cli:claude",
        "cli:gemini",
        "cli:codex",
        "cli:opencode",
        "cli:pi",
        "remote:hermes",
        "remote:omb",
        "remote:rakazo",
        "remote:herdr",
        "remote:swarm",
    ):
        assert ADAPTER_NAME_FIELD[key]["path"] == "delimiter"
        assert ADAPTER_NAME_FIELD[key]["name_field"] == "stripped"


def test_named_path_sets_name_field():
    out = apply_speaker_identity(
        [{"role": "assistant", "content": "hello", "name": "jeeves"}],
        adapter_id="openai_compat",
    )
    assert out == [{"role": "assistant", "content": "hello", "name": "jeeves"}]


def test_delimiter_path_wraps_body():
    out = apply_speaker_identity(
        [{"role": "assistant", "content": "hello", "name": "echo"}],
        adapter_id="cli:grok",
    )
    assert out[0]["content"] == f"{SPEAKER_OPEN}echo{SPEAKER_CLOSE}\nhello\n{SPEAKER_END}"
    assert "name" not in out[0]
    name, body = unwrap_speaker(out[0]["content"])
    assert name == "echo"
    assert body == "hello"


def test_wrap_is_idempotent():
    once = wrap_speaker("echo", "hello")
    assert wrap_speaker("echo", once) == once
    assert SPEAKER_CLOSE in once


def test_adapter_id_for_blueprint_maps_cli_and_api():
    assert adapter_id_for_blueprint("jeeves") == "openai_compat"
    assert adapter_id_for_blueprint("cli_agent", {"cli": "grok"}) == "cli:grok"
    assert speaker_path_for("cli:unknown") == "delimiter"
    assert speaker_path_for("openai_compat") == "named"
