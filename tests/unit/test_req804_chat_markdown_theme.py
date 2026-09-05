"""REQ-804: inline chat markdown follows light/dark theme tokens (Fixes #804)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"
BUBBLE = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "ChatMessageBubble.tsx"
AGENT_BUBBLE = (
    REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentChat" / "AgentMessageBubble.tsx"
)
MARKDOWN = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "markdown.ts"
THEME_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "theme.ts"


def _css() -> str:
    return INDEX_CSS.read_text(encoding="utf-8")


def _markdown_css(css: str) -> str:
    start = css.index("/* REQ-804: in-bubble markdown")
    end = css.index("/* Large dashboard action cards", start)
    return css[start:end]


def _chrome_css(css: str) -> str:
    start = css.index("/* REQ-804: in-bubble chrome")
    return css[start:]


def test_theme_module_still_resolves_light_dark_system():
    ts = THEME_TS.read_text(encoding="utf-8")
    assert "resolveTheme" in ts
    assert "subscribeSystemTheme" in ts
    assert "'system'" in ts


def test_index_css_reuses_grok_tokens_with_light_variants():
    css = _css()
    assert "--os-grok-code-inline: #ff5667" in css
    assert "--os-grok-link: #4194eb" in css
    light = css.split('[data-theme="light"]')[1]
    assert "--os-grok-code-inline: #c43d4e" in light
    assert "--os-grok-link: var(--color-primary)" in light


def test_chat_markdown_uses_theme_tokens_not_bare_black_white():
    md_css = _markdown_css(_css())
    for needle in (
        ".chat-md a",
        ".os-chat-md a",
        "var(--os-grok-link",
        ".chat-md code:not(pre code)",
        "var(--os-grok-code-inline",
        ".chat-md pre",
        "var(--color-base-300)",
        ".chat-md blockquote",
        ".chat-md table",
        ".chat-md th",
        ".chat-md hr",
    ):
        assert needle in md_css, needle
    lowered = md_css.lower()
    assert "#fff" not in lowered
    assert "#ffffff" not in lowered
    assert "#000" not in lowered
    assert "#000000" not in lowered
    css = _css()
    assert "#101218" not in css
    assert "#d6deeb" not in css


def test_in_bubble_chrome_uses_daisyui_tokens():
    css = _css()
    assert ".os-chat-status" in css
    assert "var(--color-base-content)" in css
    chrome = _chrome_css(css)
    for needle in (
        ".os-handoff-chip",
        ".os-briefing-popover",
        ".os-question-card",
        ".os-question-choice",
        ".os-suggestion-chip",
        ".os-attach-chip",
        ".os-chat-gap",
        ".os-chat-new",
        "var(--color-base-content)",
    ):
        assert needle in css, needle
    lowered = chrome.lower()
    assert "#fff" not in lowered
    assert "#000" not in lowered


def test_bubbles_still_render_safe_markdown():
    bubble = BUBBLE.read_text(encoding="utf-8")
    agent = AGENT_BUBBLE.read_text(encoding="utf-8")
    md = MARKDOWN.read_text(encoding="utf-8")
    assert "renderSafeMarkdown" in bubble
    assert 'data-testid="chat-md"' in bubble
    assert "chat-md" in bubble
    assert "chat-md" in agent
    assert "os-chat-md" in agent
    assert "TABLE" in md
    assert "BLOCKQUOTE" in md
    assert "HR" in md
