"""Regression: rest_mode chat JS must not sink untrusted content unsafely.

High-severity DOM XSS previously came from:
- messages.js: marked.parse(content) + raw sender into innerHTML
- rendering.js: message.content / sender into innerHTML
- chatHistory.js: raw data-full-content + innerHTML on expand
- messageProcessor.js: user message into persistent-message innerHTML
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REST_JS = ROOT / "src" / "swarm" / "static" / "rest_mode" / "js"
MESSAGES = REST_JS / "messages.js"
RENDERING = REST_JS / "rendering.js"
CHAT_HISTORY = REST_JS / "modules" / "chatHistory.js"
MESSAGE_PROCESSOR = REST_JS / "modules" / "messageProcessor.js"
HTML_SAFE = REST_JS / "htmlSafe.js"


def _slice_after(source: str, marker: str, length: int = 1200) -> str:
    idx = source.find(marker)
    assert idx != -1, f"marker not found: {marker}"
    return source[idx : idx + length]


def test_html_safe_helpers_exist():
    source = HTML_SAFE.read_text(encoding="utf-8")
    assert "export function escapeHtml" in source
    assert "export function escapeAttr" in source
    assert "export function sanitizeMarkdownHtml" in source
    assert "javascript:" in source or "isSafeUrl" in source


def test_messages_js_escapes_sender_and_sanitizes_markdown():
    source = MESSAGES.read_text(encoding="utf-8")
    assert "from './htmlSafe.js'" in source or 'from "./htmlSafe.js"' in source
    assert "escapeHtml" in source
    assert "sanitizeMarkdownHtml" in source

    body = _slice_after(source, "export function renderMessage")
    assert "escapeHtml(sender" in body
    assert "sanitizeMarkdownHtml(marked.parse(" in body
    # Raw sender must not be interpolated into the message HTML shell.
    assert re.search(r"\$\{\s*sender\s*\}", body) is None
    # marked output must go through sanitizeMarkdownHtml before innerHTML.
    assert "sanitizeMarkdownHtml(marked.parse(messageContent))" in body
    assert re.search(r"[^f]\$\{\s*marked\.parse\(", body) is None


def test_rendering_js_escapes_sender_and_content():
    source = RENDERING.read_text(encoding="utf-8")
    assert "from './htmlSafe.js'" in source or 'from "./htmlSafe.js"' in source
    body = _slice_after(source, "export function renderMessage")
    assert "escapeHtml(sender" in body
    assert "escapeHtml(message" in body
    assert re.search(r"\$\{\s*sender\s*\}", body) is None
    assert re.search(r"\$\{\s*message\.content\s*\}", body) is None

    persist = _slice_after(source, "function persistMessage")
    assert "textContent" in persist
    assert re.search(r"innerHTML\s*=\s*`[^`]*\$\{\s*sender", persist) is None
    assert re.search(r"innerHTML\s*=\s*`[^`]*message\.content", persist) is None


def test_chat_history_escapes_data_full_content_and_uses_textcontent():
    source = CHAT_HISTORY.read_text(encoding="utf-8")
    assert "escapeAttr" in source
    assert "escapeHtml" in source

    trunc = _slice_after(source, "function truncateMessage")
    assert "escapeAttr(text)" in trunc or "escapeAttr(content)" in trunc
    assert 'data-full-content="${content}"' not in trunc
    assert re.search(r'data-full-content="\$\{\s*content\s*\}"', trunc) is None

    expand = _slice_after(source, "querySelectorAll('.read-more')")
    assert "textContent" in expand
    assert "getAttribute('data-full-content')" in expand or 'getAttribute("data-full-content")' in expand
    assert re.search(
        r"parent\.innerHTML\s*=\s*parent\.getAttribute\(\s*['\"]data-full-content['\"]\s*\)",
        source,
    ) is None


def test_message_processor_persist_uses_textcontent():
    source = MESSAGE_PROCESSOR.read_text(encoding="utf-8")
    body = _slice_after(source, "persistentMessageElement")
    assert "textContent" in body
    assert re.search(
        r"innerHTML\s*=\s*`[^`]*\$\{\s*userMessageContent\s*\}",
        body,
    ) is None
