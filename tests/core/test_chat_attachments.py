"""Unit tests for local chat attachment helpers (REQ-38)."""

from __future__ import annotations

import uuid

import pytest

from swarm.core import chat_attachments


def test_safe_display_name_strips_paths():
    assert chat_attachments.safe_display_name("../../etc/passwd") == "passwd"
    assert chat_attachments.safe_display_name("") == "file"
    assert chat_attachments.safe_display_name(".") == "file"


def test_parse_attachment_ids_keeps_valid_uuids_only():
    good = str(uuid.uuid4())
    assert chat_attachments.parse_attachment_ids([good, "nope", "", None]) == [good]
    assert chat_attachments.parse_attachment_ids("not-a-list") == []


def test_compose_user_content_includes_text_excerpt():
    body = chat_attachments.compose_user_content(
        "please review",
        [
            {
                "name": "notes.txt",
                "content_type": "text/plain",
                "size": 5,
                "text": "hello",
            },
            {
                "name": "photo.png",
                "content_type": "image/png",
                "size": 2048,
            },
        ],
    )
    assert body.startswith("please review")
    assert "[Attached files]" in body
    assert "notes.txt" in body
    assert "hello" in body
    assert "photo.png" in body
    assert "2.0 KB" in body


def test_write_and_read_bytes_are_user_scoped(tmp_path):
    class _User:
        pk = 7

    aid = uuid.uuid4()
    path = chat_attachments.write_bytes(_User(), aid, b"abc", base_dir=tmp_path)
    assert path.parent.name == "u7"
    assert chat_attachments.read_bytes(_User(), aid, base_dir=tmp_path) == b"abc"


def test_excerpt_text_only_for_text_types():
    assert chat_attachments.excerpt_text(b"hi", "text/plain") == "hi"
    assert chat_attachments.excerpt_text(b"{}", "application/json") == "{}"
    assert chat_attachments.excerpt_text(b"\x00\x01", "image/png") is None
