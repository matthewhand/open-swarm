"""Browser automation honesty helpers."""
from swarm.core.browser_tools import (
    BROWSER_UNAVAILABLE,
    browser_unavailable_error,
    is_browser_unavailable_payload,
)


def test_browser_unavailable_error_shape():
    err = browser_unavailable_error()
    assert err["ok"] is False
    assert err["error"] == BROWSER_UNAVAILABLE
    assert "detail" not in err
    assert BROWSER_UNAVAILABLE == "browser automation unavailable: no playwright MCP server"


def test_browser_unavailable_error_with_detail():
    err = browser_unavailable_error(detail="npx not found")
    assert err["detail"] == "npx not found"
    assert is_browser_unavailable_payload(err)


def test_is_browser_unavailable_rejects_success_shaped():
    assert not is_browser_unavailable_payload({"ok": True, "content": "done"})
    assert not is_browser_unavailable_payload(None)
    assert not is_browser_unavailable_payload("browser automation unavailable: no playwright MCP server")
