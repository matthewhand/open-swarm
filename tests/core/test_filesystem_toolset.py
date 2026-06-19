"""Tests for the injectable filesystem toolset (safety + permission levels)."""
from __future__ import annotations

import pytest

from swarm.core.filesystem_toolset import (
    FilesystemToolset,
    PathNotAllowed,
    PermissionDenied,
    FilesystemError,
)


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("world", encoding="utf-8")
    return tmp_path


def test_read_within_allowlist(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    assert fs.read(str(sandbox / "a.txt")) == "hello"


def test_read_outside_allowlist_denied(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    with pytest.raises(PathNotAllowed):
        fs.read("/etc/passwd")


def test_list_and_stat(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    names = {e["name"] for e in fs.list(str(sandbox))}
    assert {"a.txt", "sub"} <= names
    assert fs.stat(str(sandbox / "a.txt"))["type"] == "file"


def test_readonly_blocks_write(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    with pytest.raises(PermissionDenied):
        fs.write(str(sandbox / "new.txt"), "x")


def test_none_blocks_read(sandbox):
    fs = FilesystemToolset(permission="none", allowed_paths=[str(sandbox)])
    with pytest.raises(PermissionDenied):
        fs.read(str(sandbox / "a.txt"))


def test_readwrite_allows_write(sandbox):
    fs = FilesystemToolset(permission="readwrite", allowed_paths=[str(sandbox)])
    fs.write(str(sandbox / "new.txt"), "data")
    assert fs.read(str(sandbox / "new.txt")) == "data"


def test_read_size_cap(sandbox):
    big = sandbox / "big.txt"
    big.write_text("x" * 5000, encoding="utf-8")
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)], max_read_bytes=100)
    out = fs.read(str(big))
    assert "truncated" in out and len(out) < 5000


def test_request_cannot_escalate_to_readwrite(sandbox):
    # config grants readonly; a per-request override asking for readwrite is ignored.
    cfg = {"filesystem": {"permission": "readonly", "allowed_paths": [str(sandbox)]}}
    fs = FilesystemToolset.from_config(cfg, overrides={"permission": "readwrite"})
    assert fs.permission == "readonly"
    with pytest.raises(PermissionDenied):
        fs.write(str(sandbox / "x.txt"), "y")


def test_not_a_file(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    with pytest.raises(FilesystemError):
        fs.read(str(sandbox / "sub"))  # it's a dir


def test_read_line_range(sandbox):
    (sandbox / "lines.txt").write_text("L1\nL2\nL3\nL4\nL5", encoding="utf-8")
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    out = fs.read(str(sandbox / "lines.txt"), start_line=2, end_line=3)
    assert out == "2: L2\n3: L3"


def test_grep_file_and_dir(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    # a.txt="hello", sub/b.txt="world"
    assert "a.txt:1: hello" in fs.grep("hel", str(sandbox))
    assert "no matches" in fs.grep("zzz_nomatch", str(sandbox))


def test_find_glob(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    out = fs.find("*.txt", str(sandbox))
    assert "a.txt" in out and "b.txt" in out


def test_grep_bad_regex(sandbox):
    fs = FilesystemToolset(permission="readonly", allowed_paths=[str(sandbox)])
    with pytest.raises(FilesystemError):
        fs.grep("(unclosed", str(sandbox))
