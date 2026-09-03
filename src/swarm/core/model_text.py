"""Sanitize model completions before they hit chat transcripts."""

from __future__ import annotations

import re

# Qwen/Gemma-style special tokens that leak when the gateway slug is a bad fit.
_LEAKED_SPECIAL = re.compile(
    r"<unused\d+>"
    r"|<\|(?:endoftext|im_start|im_end|end|>)\|>"
    r"|</?unused\d+>",
    re.IGNORECASE,
)

# CSI/OSC (ESC or C1) plus ESC-stripped leftovers like ``[13;28;13;1;0;1_``.
_ANSI = re.compile(
    r"(?:\x1b\[[0-9;?]*[ -/]*[@-~])"
    r"|(?:\x9b[0-9;?]*[ -/]*[@-~])"
    r"|(?:\x1b\][^\x07\x1b]*(?:\x07|\x1b\\))"
    r"|(?:\x1b[@-Z\\-_])"
    r"|(?:\[(?:\d+;){1,10}\d+[A-Za-z_~@])"
)

_ALNUM = re.compile(r"[A-Za-z0-9]+")


def sanitize_model_text(text: str | None) -> str:
    """Strip leaked tokenizer leftovers and ANSI; keep real words."""
    if not text:
        return ""
    cleaned = _LEAKED_SPECIAL.sub("", text)
    for _ in range(3):
        nxt = _ANSI.sub("", cleaned)
        if nxt == cleaned:
            break
        cleaned = nxt
    cleaned = cleaned.replace("\x1b", "").replace("\x9b", "")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def is_usable_model_text(text: str | None, *, min_alnum: int = 8) -> bool:
    """False for empty, tokenizer spam, or leftover control sequences."""
    cleaned = sanitize_model_text(text)
    if not cleaned:
        return False
    alnum = "".join(_ALNUM.findall(cleaned))
    return len(alnum) >= min_alnum
