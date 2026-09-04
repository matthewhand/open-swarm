"""REQ-56 local store helpers: size, path, missing store. No secrets."""

from pathlib import Path

from swarm.core.local_store import (
    NOT_CREATED,
    ON_THIS_MACHINE,
    format_size,
    home_relative_path,
    local_store_facts,
    looks_like_connection_string,
    safe_display_path,
)


def test_format_size():
    assert format_size(0) == "0 B"
    assert format_size(500) == "500 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(13_002_342) == "12.4 MB"
    assert format_size(-3) == "0 B"


def test_home_relative_path(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    inside = home / "share" / "swarm" / "store.db"
    inside.parent.mkdir(parents=True)
    inside.write_bytes(b"x" * 64)
    assert home_relative_path(inside) == "~/share/swarm/store.db"
    outside = tmp_path / "other" / "store.db"
    outside.parent.mkdir()
    outside.write_bytes(b"y")
    assert "secret" not in home_relative_path(outside)
    assert str(outside.resolve()) in home_relative_path(outside) or home_relative_path(outside).endswith(
        "other/store.db"
    )


def test_rejects_connection_strings():
    assert looks_like_connection_string("postgres://user:hunter2@db.example/app")
    assert looks_like_connection_string("mysql://root:pwd@localhost/x")
    assert looks_like_connection_string("user=me password=hunter2 host=db")
    assert not looks_like_connection_string("/tmp/store.db")
    assert not looks_like_connection_string("~/share/swarm/store.db")


def test_safe_display_path_strips_secrets():
    leaked = "postgres://user:hunter2@db.example:5432/app"
    assert "hunter2" not in safe_display_path(leaked, created=False)
    assert "postgres://" not in safe_display_path(leaked, created=True)
    assert safe_display_path(leaked, created=False) == NOT_CREATED
    assert safe_display_path(leaked, created=True) == ON_THIS_MACHINE


def test_missing_file_is_not_created_yet(tmp_path):
    missing = tmp_path / "no-such-store.db"
    facts = local_store_facts(
        path=missing,
        conversation_count=0,
        message_count=0,
        discover=False,
    )
    assert facts["created"] is False
    assert facts["size_bytes"] == 0
    assert facts["size_label"] == NOT_CREATED
    assert facts["conversation_count"] == 0
    assert facts["message_count"] == 0
    assert "traceback" not in str(facts).lower()
    dumped = " ".join(str(v) for v in facts.values())
    assert "django" not in dumped.lower()
    assert "sqlite" not in dumped.lower()
    assert "orm" not in dumped.lower()


def test_existing_file_reports_human_size(tmp_path):
    store = tmp_path / "store.db"
    store.write_bytes(b"\x00" * 13_002_342)
    facts = local_store_facts(
        path=store,
        conversation_count=3,
        message_count=11,
        discover=False,
    )
    assert facts["created"] is True
    assert facts["size_bytes"] == 13_002_342
    assert facts["size_label"] == "12.4 MB"
    assert facts["conversation_count"] == 3
    assert facts["message_count"] == 11
    assert "hunter2" not in facts["path"]
    assert "://" not in facts["path"]


def test_connection_string_path_never_leaks():
    facts = local_store_facts(
        path="postgres://user:hunter2@host/db",
        conversation_count=0,
        message_count=0,
        discover=False,
    )
    blob = str(facts)
    assert "hunter2" not in blob
    assert "postgres://" not in blob
    assert facts["size_label"] == NOT_CREATED
    assert facts["conversation_count"] == 0
