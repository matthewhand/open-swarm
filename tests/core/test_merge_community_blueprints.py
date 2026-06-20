"""Tests for blueprint_discovery.merge_community_blueprints.

Bundled blueprints are authoritative: a community blueprint may add new names
but must never shadow a bundled one. Missing/non-dir roots and discovery errors
are skipped silently. discover_blueprints is monkeypatched so we exercise the
merge/collision logic without real on-disk blueprint modules.
"""
from __future__ import annotations

import pytest

from swarm.core import blueprint_discovery as bd


def test_no_extra_dirs_returns_base_copy():
    base = {"alpha": "A", "beta": "B"}
    out = bd.merge_community_blueprints(base, None)
    assert out == base
    assert out is not base  # a copy, not the same object


def test_nonexistent_dir_is_skipped(monkeypatch):
    called = []
    monkeypatch.setattr(bd, "discover_blueprints", lambda *a, **k: called.append(a) or {})
    base = {"alpha": "A"}
    out = bd.merge_community_blueprints(base, ["/definitely/not/a/dir"])
    assert out == base
    assert called == []  # never descended into a non-dir


def test_merges_non_colliding_community_blueprint(monkeypatch, tmp_path):
    monkeypatch.setattr(bd, "discover_blueprints", lambda *a, **k: {"community_bp": "C"})
    base = {"alpha": "A"}
    out = bd.merge_community_blueprints(base, [str(tmp_path)])
    assert out == {"alpha": "A", "community_bp": "C"}


def test_collision_keeps_bundled_blueprint(monkeypatch, tmp_path):
    # Community root tries to provide "alpha" too — bundled wins.
    monkeypatch.setattr(bd, "discover_blueprints", lambda *a, **k: {"alpha": "SHADOW"})
    base = {"alpha": "A"}
    out = bd.merge_community_blueprints(base, [str(tmp_path)])
    assert out["alpha"] == "A"


def test_discovery_error_in_one_root_is_skipped(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise RuntimeError("broken community root")

    monkeypatch.setattr(bd, "discover_blueprints", boom)
    base = {"alpha": "A"}
    out = bd.merge_community_blueprints(base, [str(tmp_path)])
    assert out == base  # error swallowed, base intact


def test_does_not_mutate_base(monkeypatch, tmp_path):
    monkeypatch.setattr(bd, "discover_blueprints", lambda *a, **k: {"extra": "X"})
    base = {"alpha": "A"}
    bd.merge_community_blueprints(base, [str(tmp_path)])
    assert base == {"alpha": "A"}  # input untouched
