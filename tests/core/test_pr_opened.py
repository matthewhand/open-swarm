"""REQ-71: structured PR-opened payloads — no markdown scrape, no invented stats."""

from swarm.core.pr_opened import is_github_pr_url, parse_pr_opened, persist_pr_opened_message

GH = "https://github.com/matthewhand/open-swarm/pull/416"


def test_github_pr_url_is_public_https_only():
    assert is_github_pr_url(GH)
    assert is_github_pr_url(f"{GH}/files")
    assert not is_github_pr_url("http://github.com/matthewhand/open-swarm/pull/416")
    assert not is_github_pr_url("https://gitlab.com/acme/repo/pull/1")
    assert not is_github_pr_url("http://127.0.0.1:8001/pull/1")
    assert not is_github_pr_url("Opened a PR")


def test_parse_explicit_pr_opened_keeps_supplied_fields_only():
    payload = parse_pr_opened(
        {
            "type": "pr_opened",
            "url": GH,
            "number": 416,
            "title": "REQ-71 card",
            "branch": "cursor/req-71",
            "additions": 4,
            "deletions": 1,
            "opener": {"agent_id": "codey", "name": "Codey"},
        },
        agent_id="codey",
        conversation_id="conv-1",
    )
    assert payload["type"] == "pr_opened"
    assert payload["url"] == GH
    assert payload["number"] == 416
    assert payload["additions"] == 4
    assert payload["deletions"] == 1
    assert "files_changed" not in payload
    assert payload["opener"]["agent_id"] == "codey"
    assert payload["opener"]["conversation_id"] == "conv-1"


def test_parse_github_api_shape_does_not_invent_stats():
    payload = parse_pr_opened(
        {
            "html_url": GH,
            "number": 416,
            "title": "REQ-71 card",
            "head": {"ref": "feat/card"},
        }
    )
    assert payload is not None
    assert payload["branch"] == "feat/card"
    assert "additions" not in payload
    assert "deletions" not in payload


def test_parse_rejects_markdown_and_lone_links():
    assert parse_pr_opened(f"Opened {GH}") is None
    assert parse_pr_opened({"html_url": GH}) is None
    assert parse_pr_opened({"url": "https://example.com/pull/1", "type": "pr_opened"}).get("url") is None


def test_persist_status_row_is_idempotent():
    messages: list[dict] = []
    payload = {"type": "pr_opened", "url": GH, "number": 416}
    persist_pr_opened_message(messages, payload)
    persist_pr_opened_message(messages, payload)
    assert len(messages) == 1
    assert messages[0]["role"] == "status"
    assert '"type":"pr_opened"' in messages[0]["content"]
