"""Tests for cli_catalog.apply_model / with_model — model-flag pinning logic.

The catalog suite covers names/entries/starter-config/suggest, but the model
pinning branches (replace an existing pin, append when absent, no-op for a CLI
with no model flag, empty cmd, immutability) were untested.
"""
from __future__ import annotations

from swarm.core import cli_catalog as c


def test_apply_model_replaces_existing_pin():
    # opencode ships with a default --model already in its cmd.
    entry = c.catalog_entry("opencode")
    assert "--model" in entry["cmd"]
    out = c.apply_model(entry, "opencode", "opencode/new-model")
    assert out["cmd"].count("--model") == 1  # replaced, not duplicated
    i = out["cmd"].index("--model")
    assert out["cmd"][i + 1] == "opencode/new-model"


def test_apply_model_appends_flag_when_absent():
    # claude's default cmd has no --model; apply_model should append it.
    entry = c.catalog_entry("claude")
    assert "--model" not in entry["cmd"]
    out = c.apply_model(entry, "claude", "claude-test")
    assert out["cmd"][-2:] == ["--model", "claude-test"]


def test_apply_model_noop_for_cli_without_model_flag():
    # A CLI not in MODEL_FLAG (e.g. grok) is returned unchanged.
    assert "grok" not in c.MODEL_FLAG
    entry = c.catalog_entry("grok")
    out = c.apply_model(entry, "grok", "whatever")
    assert out["cmd"] == entry["cmd"]


def test_apply_model_empty_cmd_unchanged():
    out = c.apply_model({"cmd": []}, "claude", "m")
    assert out == {"cmd": []}


def test_apply_model_does_not_mutate_input():
    entry = c.catalog_entry("opencode")
    original = list(entry["cmd"])
    c.apply_model(entry, "opencode", "opencode/changed")
    assert entry["cmd"] == original  # input untouched (deep-copied)


def test_with_model_unknown_cli_is_none():
    assert c.with_model("definitely-not-a-cli", "m") is None


def test_with_model_sets_model_and_timeout():
    out = c.with_model("opencode", "opencode/pinned", timeout=300)
    assert out is not None
    i = out["cmd"].index("--model")
    assert out["cmd"][i + 1] == "opencode/pinned"
    assert out["timeout"] == 300
