"""Tests for MoA config merge / init helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm.core.moa.config import (
    DEFAULT_MOA_BLOCK,
    OPENWEBUI_MOA_CONNECTION,
    merge_moa_config,
    resolve_moa_preset,
    write_moa_config,
)


def test_merge_moa_config_defaults():
    cfg = merge_moa_config({})
    assert "moa" in cfg
    assert cfg["moa"]["backend"] == "grok"
    assert "analyst" in cfg["moa"]["participants"]
    assert "presets" in cfg["moa"]


def test_merge_preserves_existing_unless_overwrite():
    existing = {"moa": {"backend": "fake", "participants": ["only"]}, "llm": {"default": {}}}
    cfg = merge_moa_config(existing, overwrite=False)
    assert cfg["moa"]["backend"] == "fake"
    assert cfg["moa"]["participants"] == ["only"]
    # missing keys filled
    assert "permission" in cfg["moa"]
    cfg2 = merge_moa_config(existing, overwrite=True)
    assert cfg2["moa"]["backend"] == DEFAULT_MOA_BLOCK["backend"]


def test_write_moa_config(tmp_path: Path):
    path = tmp_path / "swarm_config.json"
    write_moa_config(path, backend="fake", participants=["a", "b"])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["moa"]["backend"] == "fake"
    assert data["moa"]["participants"] == ["a", "b"]


def test_resolve_moa_preset():
    moa = merge_moa_config({})["moa"]
    ci = resolve_moa_preset(moa, "ci")
    assert ci["backend"] == "fake"
    assert "fake_responses" in ci
    with pytest.raises(KeyError):
        resolve_moa_preset(moa, "nope")


def test_openwebui_connection_preset():
    assert OPENWEBUI_MOA_CONNECTION["model"] == "moa"
    assert "/v1" in OPENWEBUI_MOA_CONNECTION["base_url"]
