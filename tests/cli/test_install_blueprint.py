"""Tests for install_blueprint, including Zip Slip rejection."""
import argparse
import stat
import zipfile
from pathlib import Path

import pytest

from swarm.core import paths
from swarm.extensions.cli.commands.install_blueprint import (
    _safe_extract_zip,
    _zip_member_destination,
    _zip_member_is_symlink,
    execute,
)


@pytest.fixture
def mock_user_blueprints_dir(monkeypatch, tmp_path):
    user_blueprints_dir = tmp_path / "user_blueprints"
    user_blueprints_dir.mkdir()
    monkeypatch.setattr(paths, "get_user_blueprints_dir", lambda: user_blueprints_dir)
    return user_blueprints_dir

def _write_zip_with_member(zip_path: Path, member_name: str, content: bytes = b"pwned") -> None:
    """Create a zip whose central-directory name is exactly member_name (may include ..)."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        info = zipfile.ZipInfo(member_name)
        zf.writestr(info, content)


def _write_zip_with_symlink_member(
    zip_path: Path, member_name: str, link_target: str
) -> None:
    """Create a zip with a Unix symlink member (external_attr S_IFLNK)."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        info = zipfile.ZipInfo(member_name)
        info.create_system = 3  # Unix
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, link_target.encode("utf-8"))


def test_zip_member_is_symlink_detects_unix_mode():
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    assert _zip_member_is_symlink(info) is True
    regular = zipfile.ZipInfo("file.txt")
    assert _zip_member_is_symlink(regular) is False


def test_zip_member_destination_rejects_symlink(tmp_path):
    target = tmp_path / "dest"
    target.mkdir()
    info = zipfile.ZipInfo("escape")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError, match="Refusing zip symlink member"):
        _zip_member_destination(target, info)


def test_zip_member_destination_rejects_parent_escape(tmp_path):
    target = tmp_path / "dest"
    target.mkdir()
    evil = zipfile.ZipInfo("../outside.txt")
    with pytest.raises(ValueError, match="Unsafe zip member path"):
        _zip_member_destination(target, evil)


def test_zip_member_destination_rejects_absolute(tmp_path):
    target = tmp_path / "dest"
    target.mkdir()
    evil = zipfile.ZipInfo("/tmp/absolute.txt")
    with pytest.raises(ValueError, match="Unsafe zip member path"):
        _zip_member_destination(target, evil)


def test_safe_extract_zip_rejects_traversal_and_does_not_write_outside(tmp_path):
    target = tmp_path / "blueprint"
    target.mkdir()
    outside = tmp_path / "outside.txt"
    assert not outside.exists()

    zip_path = tmp_path / "evil.zip"
    _write_zip_with_member(zip_path, "../outside.txt", b"should-not-land")

    with zipfile.ZipFile(zip_path, "r") as zf:
        with pytest.raises(ValueError, match="Unsafe zip member path"):
            _safe_extract_zip(zf, target)

    assert not outside.exists()
    assert list(target.iterdir()) == []


def test_safe_extract_zip_rejects_symlink_and_does_not_write_outside(tmp_path):
    """Symlink member pointing outside must be refused; target stays empty."""
    target = tmp_path / "blueprint"
    target.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep-me")
    marker_mtime = outside.stat().st_mtime_ns

    zip_path = tmp_path / "symlink_evil.zip"
    _write_zip_with_symlink_member(zip_path, "escape_link", "../outside.txt")

    with zipfile.ZipFile(zip_path, "r") as zf:
        with pytest.raises(ValueError, match="Refusing zip symlink member"):
            _safe_extract_zip(zf, target)

    assert list(target.iterdir()) == []
    assert outside.read_text() == "keep-me"
    assert outside.stat().st_mtime_ns == marker_mtime
    assert not any(p.is_symlink() for p in target.rglob("*"))


def test_execute_rejects_malicious_zip_with_symlink_escape(
    capsys, mock_user_blueprints_dir, tmp_path
):
    """Install of a zip with an escaping symlink member must fail with no outside write."""
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("untouched")

    zip_path = tmp_path / "symlink_bp.zip"
    _write_zip_with_symlink_member(zip_path, "leak", "../outside_secret.txt")

    args = argparse.Namespace(name_or_path=str(zip_path), overwrite=False)
    execute(args)

    captured = capsys.readouterr().out
    assert "Error during installation" in captured
    assert "Refusing zip symlink member" in captured
    assert "installed successfully" not in captured
    assert outside.read_text() == "untouched"
    installed = mock_user_blueprints_dir / "symlink_bp"
    if installed.exists():
        assert not any(p.is_symlink() for p in installed.rglob("*"))


def test_execute_rejects_malicious_zip_with_parent_escape(
    capsys, mock_user_blueprints_dir, tmp_path
):
    """Crafted zip with ../ must be rejected; file must not appear outside target."""
    outside_dir = tmp_path / "escape_zone"
    outside_dir.mkdir()
    escape_file = outside_dir / "pwned.txt"

    zip_path = tmp_path / "malicious_bp.zip"
    # Extract root is user_blueprints/malicious_bp/; ../../escape_zone/pwned.txt
    # would resolve to tmp_path/escape_zone/pwned.txt without confinement.
    _write_zip_with_member(zip_path, "../../escape_zone/pwned.txt", b"owned")

    args = argparse.Namespace(name_or_path=str(zip_path), overwrite=False)
    execute(args)

    captured = capsys.readouterr().out
    assert "Error during installation" in captured
    assert "Unsafe zip member path" in captured
    assert not escape_file.exists()
    assert "installed successfully" not in captured


def test_execute_extracts_benign_zip(capsys, mock_user_blueprints_dir, tmp_path):
    zip_path = tmp_path / "good_bp.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("hello.py", "print('hi')\n")

    args = argparse.Namespace(name_or_path=str(zip_path), overwrite=False)
    execute(args)

    captured = capsys.readouterr().out
    assert "installed successfully" in captured
    dest = mock_user_blueprints_dir / "good_bp" / "hello.py"
    assert dest.is_file()
    assert dest.read_text() == "print('hi')\n"
