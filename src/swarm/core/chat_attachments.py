"""Local-disk chat attachments (REQ-38).

Files live under ``SWARM_ATTACHMENTS_DIR`` or
``<SWARM_USER_DATA_DIR>/attachments/<user_key>/<id>``. Metadata is Django
sqlite (``ChatAttachment``). No Neon. Filenames are never used as paths.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from swarm.core.chat_store import user_key_for
from swarm.core.paths import get_user_data_dir_for_swarm

ENV_ATTACH_DIR = "SWARM_ATTACHMENTS_DIR"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TEXT_EXCERPT_BYTES = 32 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 8

_TEXT_TYPES = frozenset(
    {
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-javascript",
        "application/yaml",
        "application/x-yaml",
        "application/toml",
        "application/sql",
    }
)
def store_dir(*, base_dir: Path | None = None) -> Path:
    """Root of the attachment byte store."""
    if base_dir is not None:
        return Path(base_dir)
    env = (os.environ.get(ENV_ATTACH_DIR) or "").strip()
    if env:
        return Path(env)
    return get_user_data_dir_for_swarm() / "attachments"


def safe_display_name(name: str | None) -> str:
    """Basename only; never a path. Empty becomes ``file``."""
    text = Path(name or "").name.strip()
    if not text or text in {".", ".."}:
        return "file"
    return text[:512]


def attachment_path(user, attachment_id, *, base_dir: Path | None = None) -> Path:
    """Absolute path for one attachment. ``attachment_id`` is a UUID string."""
    aid = str(attachment_id).strip()
    uuid.UUID(aid)
    return store_dir(base_dir=base_dir) / user_key_for(user) / aid


def is_text_content_type(content_type: str) -> bool:
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if not ctype:
        return False
    if ctype.startswith("text/"):
        return True
    return ctype in _TEXT_TYPES


def write_bytes(user, attachment_id, data: bytes, *, base_dir: Path | None = None) -> Path:
    """Write attachment bytes. Caller enforces size limits."""
    path = attachment_path(user, attachment_id, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def read_bytes(user, attachment_id, *, base_dir: Path | None = None) -> bytes:
    path = attachment_path(user, attachment_id, base_dir=base_dir)
    return path.read_bytes()


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def caption(names: list[str]) -> str:
    if not names:
        return "Attached file"
    if len(names) == 1:
        return f"Attached {names[0]}"
    return f"Attached {', '.join(names)}"


def excerpt_text(data: bytes, content_type: str) -> str | None:
    if not is_text_content_type(content_type):
        return None
    snippet = data[:MAX_TEXT_EXCERPT_BYTES]
    return snippet.decode("utf-8", errors="replace")


def compose_user_content(display_text: str, attachments: list[dict[str, Any]]) -> str:
    """User bubble text plus attachment bodies for model context."""
    parts: list[str] = []
    text = (display_text or "").strip()
    if text:
        parts.append(text)
    if not attachments:
        return text
    blocks: list[str] = []
    for item in attachments:
        name = safe_display_name(str(item.get("name") or "file"))
        ctype = str(item.get("content_type") or "application/octet-stream")
        size = int(item.get("size") or 0)
        header = f"- {name} ({ctype}, {format_size(size)})"
        body = item.get("text")
        if isinstance(body, str) and body:
            blocks.append(f"{header}\n{body}")
        else:
            blocks.append(header)
    parts.append("[Attached files]\n" + "\n".join(blocks))
    return "\n\n".join(parts)


def parse_attachment_ids(raw) -> list[str]:
    """Normalize a frame's ``attachments`` list to UUID strings."""
    if not isinstance(raw, list):
        return []
    ids: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        try:
            ids.append(str(uuid.UUID(text)))
        except (ValueError, TypeError, AttributeError):
            continue
        if len(ids) >= MAX_ATTACHMENTS_PER_MESSAGE:
            break
    return ids
