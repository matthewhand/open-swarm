"""Offline regression tests for live-suite opt-in and evidence boundaries."""
import pytest

from tests.live.support import connection, instance_ids, reply_text


def test_no_url_never_uses_default_or_operator_key(monkeypatch):
    monkeypatch.setenv("TRUEFORGE_API_KEY", "operator-secret")
    assert connection("trueforge", {}) is None
    spec, timeout, target = connection("trueforge", {"SWARM_LIVE_TRUEFORGE_URL": "http://localhost:1"})
    assert spec.api_key == spec.cookie == target == ""
    assert timeout == 90


def test_named_instance_has_independent_credentials():
    env = {"SWARM_LIVE_INSTANCES": "trueforge_second", "SWARM_LIVE_TRUEFORGE_SECOND_KIND": "trueforge",
           "SWARM_LIVE_TRUEFORGE_SECOND_URL": "https://example.test", "SWARM_LIVE_TRUEFORGE_SECOND_API_KEY": "test-key"}
    assert "trueforge_second" in instance_ids(env)
    spec, _, _ = connection("trueforge_second", env)
    assert spec.kind == "trueforge" and spec.api_key == "test-key"


@pytest.mark.parametrize("url", ["file:///example", "https://user:secret@example.test", "https://example.test?key=secret"])
def test_credential_bearing_or_invalid_urls_rejected(url):
    with pytest.raises(ValueError):
        connection("trueforge", {"SWARM_LIVE_TRUEFORGE_URL": url})


@pytest.mark.parametrize("timeout", ["nan", "inf", "0", "301"])
def test_timeout_bounded(timeout):
    with pytest.raises(ValueError):
        connection("trueforge", {"SWARM_LIVE_TRUEFORGE_URL": "https://example.test", "SWARM_LIVE_TRUEFORGE_TIMEOUT": timeout})


def test_receipt_and_echo_are_not_answers():
    assert reply_text({"prompt": "42", "job_id": "42", "status": "accepted"}) == ""
    assert reply_text({"text": "42"}) == "42"
    assert reply_text({"choices": [{"message": {"content": "42"}}]}) == "42"


def test_unconfigured_check_never_constructs_adapter(monkeypatch, caplog, capsys):
    from swarm.remotes import registry
    from tests.live.test_remote_integrations import test_live_remote as run_check

    monkeypatch.delenv("SWARM_LIVE_TRUEFORGE_URL", raising=False)
    monkeypatch.setattr(registry, "create_remote_adapter", lambda *_: pytest.fail("unexpected network adapter"))
    with pytest.raises(pytest.skip.Exception):
        run_check("trueforge", "inference", caplog, capsys)


@pytest.mark.parametrize("mode", ["answer", "receipt", "exception", "http_error"])
def test_live_check_accepts_only_completed_answer(mode, monkeypatch, caplog, capsys):
    import re
    from types import SimpleNamespace

    from swarm.remotes import registry
    from tests.live.test_remote_integrations import test_live_remote as run_check

    monkeypatch.setenv("SWARM_LIVE_TRUEFORGE_URL", "http://localhost:1")

    def send(prompt, timeout, *, target, session_id):
        assert timeout == 90 and session_id is None and target == ""
        if mode == "exception":
            raise RuntimeError("private-credential-do-not-print")
        a, b = re.search(r"calculate (\d+) \+ (\d+)", prompt).groups()
        data = {"text": str(int(a) + int(b))} if mode == "answer" else {"job_id": "accepted"}
        return SimpleNamespace(ok=mode != "http_error", http_status=401 if mode == "http_error" else 202, data=data)

    monkeypatch.setattr(registry, "create_remote_adapter", lambda *_: SimpleNamespace(send=send))
    if mode == "answer":
        run_check("trueforge", "inference", caplog, capsys)
    else:
        with pytest.raises(pytest.fail.Exception) as failure:
            run_check("trueforge", "inference", caplog, capsys)
        assert "private-credential-do-not-print" not in str(failure.value)
