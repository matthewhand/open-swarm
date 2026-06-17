"""Tests for the built-in CLI adapter catalog (swarm-cli cli-agents --suggest)."""

from __future__ import annotations

from swarm.core import cli_catalog
from swarm.core.cli_adapter import CliAdapter


def test_catalog_names_are_sorted_and_known():
    names = cli_catalog.catalog_names()
    assert names == sorted(names)
    assert {"claude", "gemini", "codex", "opencode"} <= set(names)


def test_every_catalog_entry_is_a_valid_adapter_config():
    # The catalog must never ship a config the adapter layer would reject.
    for name in cli_catalog.catalog_names():
        adapter = CliAdapter.from_config(name, cli_catalog.catalog_entry(name))
        assert adapter.name == name
        assert adapter.config.cmd[0]  # has an executable


def test_catalog_entry_returns_a_copy():
    a = cli_catalog.catalog_entry("claude")
    a["cmd"].append("--mutated")
    a["mode"] = "tampered"
    b = cli_catalog.catalog_entry("claude")
    assert "--mutated" not in b["cmd"]
    assert b["mode"] == "write"


def test_catalog_entry_unknown_is_none():
    assert cli_catalog.catalog_entry("nope-not-real") is None
    assert cli_catalog.executable_for("nope-not-real") is None


def test_executable_for():
    assert cli_catalog.executable_for("gemini") == "gemini"


def test_gemini_default_includes_skip_trust_gotcha():
    # gemini refuses to run in an untrusted dir without this; regression guard.
    assert "--skip-trust" in cli_catalog.catalog_entry("gemini")["cmd"]


def test_opencode_default_pins_a_model_gotcha():
    # opencode's built-in default model errors as "not supported".
    cmd = cli_catalog.catalog_entry("opencode")["cmd"]
    assert "--model" in cmd and cmd[cmd.index("--model") + 1]


def test_build_starter_config_wires_every_mode():
    cfg = cli_catalog.build_starter_config(["claude", "gemini"])
    assert set(cfg["cli_agents"]) == {"claude", "gemini"}
    assert cfg["llm"]["default"]["provider"] == "openai"  # passes config validation
    # claude preferred as judge/router/reducer/planner
    assert cfg["cli_fusion"]["presets"]["all"]["judge"] == "claude"
    assert cfg["cli_fusion"]["presets"]["all"]["panel"] == ["claude", "gemini"]
    assert cfg["cli_orchestrator"]["router"] == "claude"
    assert cfg["cli_map"]["planner"] == "claude"
    assert cfg["cli_map"]["workers"] == ["claude", "gemini"]


def test_build_starter_config_prefers_first_when_no_claude():
    cfg = cli_catalog.build_starter_config(["gemini", "opencode"])
    assert cfg["cli_fusion"]["default_cli"] == "gemini"  # sorted-first fallback


def test_grok_is_in_catalog():
    e = cli_catalog.catalog_entry("grok")
    assert e["cmd"][0] == "grok" and e["parse"] == "json:.text"
    assert "--always-approve" in e["cmd"]


def test_build_starter_config_prefers_grok_for_single_agent_roles():
    cfg = cli_catalog.build_starter_config(["claude", "grok", "gemini"])
    # grok preferred for every single-agent / judge role...
    assert cfg["cli_fusion"]["default_cli"] == "grok"
    assert cfg["cli_fusion"]["presets"]["all"]["judge"] == "grok"
    assert cfg["cli_orchestrator"]["router"] == "grok"
    assert cfg["cli_map"]["planner"] == "grok" and cfg["cli_map"]["reducer"] == "grok"
    # ...but the panel includes every CLI (others tapped only for multi-agent)
    assert set(cfg["cli_fusion"]["presets"]["all"]["panel"]) == {"claude", "grok", "gemini"}


def test_build_starter_config_empty_host_still_valid():
    cfg = cli_catalog.build_starter_config([])
    assert cfg["cli_agents"] == {}
    assert "llm" in cfg
    assert "cli_fusion" not in cfg  # nothing to wire


def test_build_starter_config_round_trips_through_registry():
    # Whatever it generates must be loadable by the adapter registry.
    from swarm.core.cli_adapter import CliAdapterRegistry

    cfg = cli_catalog.build_starter_config(["claude", "codex", "opencode"])
    reg = CliAdapterRegistry.from_config(cfg)
    assert set(reg.names()) == {"claude", "codex", "opencode"}


def test_suggest_skips_already_configured():
    s = cli_catalog.suggest_unconfigured(["claude", "gemini"], installed_only=False)
    assert "claude" not in s and "gemini" not in s
    assert "codex" in s and "opencode" in s


def test_suggest_all_when_nothing_configured():
    s = cli_catalog.suggest_unconfigured([], installed_only=False)
    assert set(s) == set(cli_catalog.catalog_names())


def test_suggest_installed_only_filters_by_path(monkeypatch):
    # Only 'codex' resolves on PATH -> only codex is suggested.
    def fake_which(exe):
        return "/usr/bin/codex" if exe == "codex" else None

    monkeypatch.setattr(cli_catalog.shutil, "which", fake_which)
    s = cli_catalog.suggest_unconfigured([], installed_only=True)
    assert set(s) == {"codex"}


def test_suggest_returns_deep_copies(monkeypatch):
    monkeypatch.setattr(cli_catalog.shutil, "which", lambda exe: "/x")
    s = cli_catalog.suggest_unconfigured([], installed_only=True)
    s["claude"]["cmd"].append("--mutated")
    assert "--mutated" not in cli_catalog.CATALOG["claude"]["cmd"]


def test_grok_has_native_consensus():
    assert cli_catalog.has_native_consensus("grok") is True
    assert cli_catalog.has_native_consensus("claude") is False


def test_native_consensus_flags_substitutes_n():
    assert cli_catalog.native_consensus_flags("grok", 3) == ["--best-of-n", "3"]
    assert cli_catalog.native_consensus_flags("grok", 1) == ["--best-of-n", "2"]  # clamped >=2
    assert cli_catalog.native_consensus_flags("claude", 3) is None


def test_with_native_consensus_appends_flag():
    entry = cli_catalog.with_native_consensus("grok", 4)
    assert entry["cmd"][-2:] == ["--best-of-n", "4"]
    assert entry["parse"] == "json:.text"  # base entry preserved
    assert cli_catalog.with_native_consensus("claude", 2) is None  # no native mode


def test_with_native_consensus_does_not_mutate_catalog():
    cli_catalog.with_native_consensus("grok", 2)
    assert "--best-of-n" not in cli_catalog.CATALOG["grok"]["cmd"]


def test_with_model_appends_flag_for_gemini():
    entry = cli_catalog.with_model("gemini", "gemini-3-pro-preview", timeout=600)
    assert entry["cmd"][-2:] == ["-m", "gemini-3-pro-preview"]
    assert entry["timeout"] == 600
    assert entry["parse"] == "json:.response"  # base entry preserved


def test_with_model_replaces_existing_model_for_opencode():
    # opencode pins a default --model; with_model must replace, not duplicate it.
    entry = cli_catalog.with_model("opencode", "opencode/other")
    assert entry["cmd"].count("--model") == 1
    assert entry["cmd"][entry["cmd"].index("--model") + 1] == "opencode/other"


def test_with_model_unknown_cli_is_none():
    assert cli_catalog.with_model("nope", "x") is None


def test_with_model_no_flag_known_returns_entry_unchanged():
    # grok has no MODEL_FLAG entry: return the base entry, don't guess a flag.
    base = cli_catalog.catalog_entry("grok")
    assert cli_catalog.with_model("grok", "whatever")["cmd"] == base["cmd"]


def test_with_model_does_not_mutate_catalog():
    cli_catalog.with_model("gemini", "gemini-3-pro-preview")
    assert "-m" not in cli_catalog.CATALOG["gemini"]["cmd"]


def test_apply_model_noop_on_entry_without_cmd():
    # Pinning a model on a cmd-less entry must not fabricate a flag-only cmd.
    assert cli_catalog.apply_model({"parse": "text"}, "gemini", "m") == {"parse": "text"}


def test_with_model_unknown_flag_cli_returns_entry_unchanged():
    base = cli_catalog.catalog_entry("grok")  # grok has no MODEL_FLAG
    assert cli_catalog.with_model("grok", "anything")["cmd"] == base["cmd"]
