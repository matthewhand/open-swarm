"""REQ-64: Herdr is an opt-in remotes kind. No live LAN. No tokens."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from swarm.core import remotes as remotes_core
from swarm.herdr import (
    HERDR_NOT_CONFIGURED,
    HerdrClient,
    cli_remote_from_base,
    is_localhost_base,
)
from swarm.herdr.remote import KIND_ID


class _Router(BaseHTTPRequestHandler):
    routes: dict[tuple[str, str], tuple[int, dict | list | str]] = {}

    def _handle(self, method: str) -> None:
        key = (method, self.path.split("?", 1)[0])
        status, body = self.routes.get(key, (404, {"error": "no route"}))
        payload = json.dumps(body).encode("utf-8") if not isinstance(body, str) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def http_router():
    server = HTTPServer(("127.0.0.1", 0), _Router)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = "127.0.0.1", server.server_address[1]
    yield host, port, _Router
    server.shutdown()
    _Router.routes = {}


def test_kind_id_is_herdr():
    assert KIND_ID == "herdr"
    assert "herdr" in remotes_core.REMOTE_IDS
    assert "herdr" in remotes_core.OPT_IN_REMOTE_IDS
    labels = {item["id"]: item["label"] for item in remotes_core.remote_kind_catalog()}
    assert labels["herdr"] == "Herdr"
    assert labels["omb"] == "OpenMousBot"


def test_unconfigured_herdr_is_absent_and_errors():
    cfg = {"llm": {}, "remotes": {}}
    assert "herdr" not in remotes_core.load_all_remotes(cfg)
    assert remotes_core.load_placed_members(cfg) == ["hermes", "omb", "rakazo"]
    with pytest.raises(remotes_core.RemoteError, match="not configured"):
        remotes_core.load_remote("herdr", cfg)
    health = remotes_core.check_health("herdr", config=cfg, timeout=0.2)
    assert health.ok is False
    assert "not configured" in health.detail
    assert "10.0.0." not in health.detail
    listed = remotes_core.operate("herdr", "list", config=cfg)
    assert listed.ok is False
    assert "not configured" in listed.detail


def test_herdr_default_is_not_a_lan_host():
    spec = remotes_core.default_spec("herdr")
    assert spec.base_url == ""
    assert "10.0.0." not in spec.base_url
    assert "10.0.0." not in spec.notes or "No baked LAN" in spec.notes


def test_persist_herdr_then_it_appears(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {}}), encoding="utf-8")
    monkeypatch.delenv("HERDR_BASE_URL", raising=False)
    spec, path = remotes_core.persist_remote(
        "herdr",
        base_url="http://127.0.0.1:9",
        api_key="${HERDR_API_KEY}",
        config_path=cfg,
    )
    assert path == cfg
    assert spec.id == "herdr"
    assert spec.base_url == "http://127.0.0.1:9"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["remotes"]["herdr"]["base_url"] == "http://127.0.0.1:9"
    assert data["remotes"]["herdr"]["api_key"] == "${HERDR_API_KEY}"
    assert "sk-" not in cfg.read_text(encoding="utf-8")
    loaded = remotes_core.load_all_remotes(data)
    assert "herdr" in loaded
    pub = loaded["herdr"].public_dict()
    assert pub["kind"] == "herdr"
    assert pub["api_key_set"] is False


def test_cli_remote_uses_configured_base_localhost_omits_flag():
    assert is_localhost_base("http://127.0.0.1:9")
    assert cli_remote_from_base("http://127.0.0.1:9") == ""
    assert cli_remote_from_base("http://localhost:9") == ""
    assert cli_remote_from_base("http://herdr.example.test:9") == "http://herdr.example.test:9"
    with pytest.raises(ValueError, match="not configured"):
        cli_remote_from_base("")


def test_from_remote_config_uses_configured_base(monkeypatch):
    calls: list[list[str]] = []

    def runner(argv, timeout=None):
        calls.append(list(argv))
        return __import__("subprocess").CompletedProcess(argv, 0, '{"ok":true}', "")

    cfg = {"remotes": {"herdr": {"base_url": "http://127.0.0.1:9"}}}
    monkeypatch.delenv("HERDR_BASE_URL", raising=False)
    HerdrClient.from_remote_config(cfg, runner=runner).agent_list()
    assert calls[0] == ["herdr", "agent", "list"]
    assert "--remote" not in calls[0]

    calls.clear()
    cfg = {"remotes": {"herdr": {"base_url": "http://herdr.example.test:9"}}}
    HerdrClient.from_remote_config(cfg, runner=runner).agent_list()
    assert calls[0][:3] == ["herdr", "--remote", "http://herdr.example.test:9"]

    with pytest.raises(remotes_core.RemoteError, match="not configured"):
        HerdrClient.from_remote_config({"remotes": {}}, runner=runner)


def test_herdr_health_and_list_stub_http(http_router, monkeypatch):
    host, port, router = http_router
    router.routes = {
        ("GET", "/health"): (200, {"status": "ok", "app": "herdr"}),
        (
            "GET",
            "/agents",
        ): (
            200,
            {"agents": [{"pane_id": "w3:p1", "state": "idle", "name": "grok"}]},
        ),
    }
    monkeypatch.delenv("HERDR_BASE_URL", raising=False)
    cfg = {
        "llm": {},
        "remotes": {"herdr": {"base_url": f"http://{host}:{port}", "api_key": "${HERDR_API_KEY}"}},
    }
    health = remotes_core.check_health("herdr", config=cfg, timeout=2.0)
    assert health.ok is True
    assert health.state == "UP"
    listed = remotes_core.operate("herdr", "list", config=cfg)
    assert listed.ok is True
    names = [item["name"] for item in listed.data["members"]]
    assert names == ["w3:p1"]
    assert listed.data["members"][0]["kind"] == "herdr"


def test_herdr_not_configured_constant_mentions_settings():
    assert "Settings" in HERDR_NOT_CONFIGURED
    assert "api-key-env" in HERDR_NOT_CONFIGURED
    assert "10.0.0." not in HERDR_NOT_CONFIGURED
