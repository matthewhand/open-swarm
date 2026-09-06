"""REQ-49: API vs CLI vs remote classification."""

from swarm.core.agent_kind import can_edit_agent_messages, classify_agent_kind


def test_api_blueprints_are_editable():
    assert classify_agent_kind("jeeves") == "api"
    assert classify_agent_kind("cli_agent") == "api"
    assert classify_agent_kind("support") == "api"
    assert can_edit_agent_messages("codey") is True


def test_cli_and_remote_prefixes_are_not_editable():
    assert classify_agent_kind("cli:grok") == "cli"
    assert classify_agent_kind("remote:acp") == "remote"
    assert classify_agent_kind("placeholder:remote:acp") == "remote"
    assert can_edit_agent_messages("cli:grok") is False
    assert can_edit_agent_messages("remote:acp") is False


def test_explicit_kind_wins():
    assert classify_agent_kind("jeeves", explicit="cli") == "cli"
    assert classify_agent_kind("cli:grok", explicit="api") == "api"
    assert can_edit_agent_messages("jeeves", explicit="remote") is False


def test_herdr_and_remote_impls_classify_as_remote():
    assert classify_agent_kind("herdr") == "remote"
    assert classify_agent_kind("herdr:w3:p1") == "remote"
    assert classify_agent_kind("pane", explicit="herdr") == "remote"
    assert classify_agent_kind("hermes") == "remote"
    assert classify_agent_kind("omb") == "remote"
    assert can_edit_agent_messages("herdr") is False
    assert classify_agent_kind("swarm") == "api"
