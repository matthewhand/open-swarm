"""REQ-45 this-machine Playwright driver — stubbed; missing Chrome does not crash."""
from swarm.core.browser_control import (
    BROWSER_CHROME_MISSING,
    BROWSER_PLAYWRIGHT_MISSING,
    BROWSER_TARGET_TODO,
    DEFAULT_BROWSER_TARGET,
    TARGET_SAAS,
    TARGET_SANDBOX,
    TARGET_THIS_MACHINE,
    BrowserUnavailable,
    StubBrowser,
    catalog_payload,
    open_this_machine,
    run_navigate,
    run_snapshot,
    target_not_implemented,
)


def test_catalog_defaults_to_this_machine_and_marks_todo_rows():
    payload = catalog_payload()
    assert payload["default"] == TARGET_THIS_MACHINE == DEFAULT_BROWSER_TARGET
    by_id = {row["id"]: row for row in payload["targets"]}
    assert by_id[TARGET_THIS_MACHINE]["wired"] is True
    assert by_id[TARGET_THIS_MACHINE]["default"] is True
    assert by_id[TARGET_SANDBOX]["todo"] is True
    assert by_id[TARGET_SANDBOX]["wired"] is False
    assert by_id[TARGET_SAAS]["todo"] is True
    assert payload["desktop_os"] == "out_of_scope"


def test_navigate_and_snapshot_with_stub():
    stub = StubBrowser()
    opened = open_this_machine(driver=stub)
    nav = run_navigate("https://example.com/path", driver=opened)
    assert nav["ok"] is True
    assert nav["url"] == "https://example.com/path"
    snap = run_snapshot(driver=opened)
    assert snap["ok"] is True
    assert "example.com" in snap["text"]
    opened.close()
    assert stub.closed is True


def test_sandbox_and_saas_are_todo_not_pretend_success():
    for target in (TARGET_SANDBOX, TARGET_SAAS):
        result = run_navigate("https://example.com", target=target)
        assert result["ok"] is False
        assert result["error"] == BROWSER_TARGET_TODO
        assert "TODO" in target_not_implemented(target)["error"]


def test_missing_playwright_factory_is_error_not_crash():
    def boom():
        raise BrowserUnavailable(BROWSER_PLAYWRIGHT_MISSING)

    result = run_navigate("https://example.com", playwright_factory=boom)
    assert result["ok"] is False
    assert result["error"] == BROWSER_PLAYWRIGHT_MISSING
    assert result.get("target") == TARGET_THIS_MACHINE


def test_missing_chrome_factory_is_error_not_crash():
    def no_chrome():
        raise BrowserUnavailable(BROWSER_CHROME_MISSING)

    result = run_navigate("https://example.com", playwright_factory=no_chrome)
    assert result["ok"] is False
    assert result["error"] == BROWSER_CHROME_MISSING


def test_snapshot_without_session_is_honest_error():
    result = run_snapshot()
    assert result["ok"] is False
    assert "session" in result["error"]


def test_rejects_non_http_url_on_stub():
    stub = StubBrowser()
    result = run_navigate("file:///etc/passwd", driver=stub)
    assert result["ok"] is False
    assert stub.current_url == "about:blank"
