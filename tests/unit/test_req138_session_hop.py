"""REQ-138 / #531 source lock — quota hop, not new-chat-per-task, not :8001."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "src" / "swarm" / "core" / "cli_session_hop.py"
API = REPO / "src" / "swarm" / "views" / "cli_session_hop_api.py"
URLS = REPO / "src" / "swarm" / "urls.py"
DOCS = REPO / "docs" / "CLI_FUSION.md"
CHAT = REPO / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"
HOP_TS = REPO / "webui" / "frontend" / "src" / "lib" / "cliSessionHop.ts"
CI = REPO / ".github" / "workflows" / "req138-session-hop.yml"
AGENT = REPO / "src" / "swarm" / "blueprints" / "cli_agent" / "blueprint_cli_agent.py"
CONSUMERS = REPO / "src" / "swarm" / "consumers.py"


def test_hop_is_new_session_plus_inject_not_resume():
    core = CORE.read_text(encoding="utf-8")
    assert "always a new session" in core.lower() or "new session" in core.lower()
    assert "never resume" in core.lower() or "Never resumes" in core
    assert "automated" in core.lower() and "failover" in core.lower()
    assert "WAVE" not in core
    assert ":8001" not in core
    assert "sk-" not in core or "sk-[A-Za-z" in core  # pattern only


def test_api_and_urls_are_github_only():
    api = API.read_text(encoding="utf-8")
    urls = URLS.read_text(encoding="utf-8")
    assert "v1/cli-sessions/hop/" in urls
    assert "CliSessionHopAPIView" in api
    assert ":8001" not in api
    assert "WAVE" not in api
    assert "localhost" not in api


def test_cli_agent_consumes_pending_hop():
    agent = AGENT.read_text(encoding="utf-8")
    assert "prepare_cli_turn" in agent
    assert "context_carried_chunk" in agent


def test_api_consumer_uses_real_user_key():
    consumers = CONSUMERS.read_text(encoding="utf-8")
    assert "_hop_user_key" in consumers
    assert 'apply_api_hop_messages("u0"' not in consumers
    assert "user_key_for" in consumers
    assert ":8001" not in consumers


def test_spa_calls_hop_on_cli_dropdown_switch():
    chat = CHAT.read_text(encoding="utf-8")
    hop = HOP_TS.read_text(encoding="utf-8")
    assert "hopCliSession" in chat
    assert "CLI_SESSION_HOPPED_EVENT" in hop
    assert "Carried" in hop
    assert "WAVE" not in hop
    assert ":8001" not in hop


def test_docs_and_own_diff_ci():
    docs = DOCS.read_text(encoding="utf-8")
    assert "REQ-138" in docs or "#531" in docs
    assert "summary inject" in docs.lower() or "summary" in docs.lower()
    ci = CI.read_text(encoding="utf-8")
    assert "req138" in ci.lower() or "REQ-138" in ci
    assert "pytest" in ci
    assert "vitest" in ci
