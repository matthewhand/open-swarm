"""REQ-79 / #424 — self-update parse + unused-tools + honest live probe."""

from __future__ import annotations

from unittest.mock import patch

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.self_update import (
    CLOUD_VM_DEVIATION,
    LIVE_ENV,
    OPERATOR_CHECKLIST,
    TARGET_OWNER_REPO,
    extract_github_pr_url,
    live_pr_capability,
    parse_cli_pr_opened,
)

GH = "https://github.com/matthewhand/open-swarm/pull/416"


class _PlainBlueprint(BlueprintBase):
    async def run(self, messages, **kwargs):
        yield {"messages": [{"role": "assistant", "content": "ok"}]}

    @property
    def metadata(self):
        return {"title": "Plain", "description": "no tools"}


def test_extract_url_from_gh_json_and_line():
    assert extract_github_pr_url(f'{{"url":"{GH}","number":416,"title":"card"}}') == GH
    assert extract_github_pr_url(f"Opened {GH}\nnext") == GH
    assert extract_github_pr_url("Opened a PR") is None
    assert extract_github_pr_url("http://127.0.0.1:8001/pull/1") is None
    assert extract_github_pr_url("https://example.com/pull/1") is None


def test_parse_cli_pr_opened_takes_number_from_url():
    payload = parse_cli_pr_opened(
        f"https://github.com/matthewhand/open-swarm/pull/416",
        agent_id="cli_agent",
        conversation_id="conv-1",
    )
    assert payload is not None
    assert payload["type"] == "pr_opened"
    assert payload["url"] == GH
    assert payload["number"] == 416
    assert payload["opener"]["agent_id"] == "cli_agent"
    assert "title" not in payload


def test_parse_cli_pr_opened_keeps_gh_json_title():
    payload = parse_cli_pr_opened(
        '{"url":"%s","number":416,"title":"REQ-71 card"}' % GH
    )
    assert payload["title"] == "REQ-71 card"
    assert payload["number"] == 416


def test_parse_cli_pr_opened_never_invents():
    assert parse_cli_pr_opened("") is None
    assert parse_cli_pr_opened("see the PR I opened") is None
    assert parse_cli_pr_opened("https://gitlab.com/acme/repo/pull/1") is None


def test_checklist_names_in_app_path_and_honesty():
    blob = "\n".join(OPERATOR_CHECKLIST)
    assert TARGET_OWNER_REPO in blob
    assert "self-update-pr" in blob
    assert "#root" in blob
    assert "Folder" in blob
    assert "Never invent" in blob
    assert "Restored" not in blob or "never a fake restore" in blob
    assert ":8001" not in blob
    assert "neon" not in blob.lower()
    assert "WAVE" not in blob


def test_live_probe_is_honest_without_flag(monkeypatch):
    monkeypatch.delenv(LIVE_ENV, raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    cap = live_pr_capability()
    assert cap["target"] == TARGET_OWNER_REPO
    assert cap["live_pr_url"] is None
    assert cap["can_live"] is False
    assert any(LIVE_ENV in reason for reason in cap["reasons"])
    if cap["cursor_cloud"]:
        assert CLOUD_VM_DEVIATION in (cap["deviation"] or "")


def test_live_probe_still_false_on_cloud_even_with_flag(monkeypatch):
    monkeypatch.setenv(LIVE_ENV, "1")
    with patch("swarm.core.self_update.looks_like_cursor_cloud", return_value=True):
        with patch("swarm.core.self_update.shutil.which", return_value="/usr/bin/gh"):
            cap = live_pr_capability()
    assert cap["can_live"] is False
    assert cap["live_pr_url"] is None
    assert any("Cursor cloud" in reason for reason in cap["reasons"])


def test_make_agent_unused_tools_does_not_crash():
    bp = _PlainBlueprint("plain", config={"settings": {}})
    created = []

    class FakeAgent:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.name = kwargs["name"]
            self.tools = kwargs["tools"]

    with patch.object(bp, "_get_model_instance", return_value="model"):
        with patch.object(bp, "_resolve_llm_profile", return_value={}):
            with patch.object(bp, "_get_memory_instance", return_value=None):
                with patch("agents.Agent", FakeAgent):
                    none_tools = bp.make_agent("plain", "just talk", None)
                    empty_tools = bp.make_agent("plain2", "just talk", [])

    assert none_tools.tools == []
    assert empty_tools.tools == []
    assert created[0]["tools"] == []
    assert created[1]["tools"] == []
    assert created[0]["mcp_servers"] == []
