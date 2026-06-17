"""Tests for the single-CLI blueprint (cli_agent) and shared support helpers."""

from __future__ import annotations

import sys

import pytest

from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint
from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.cli_adapter import CliAdapterRegistry

PY = sys.executable


def _echo_config(prefix: str = "ECHO") -> dict:
    return {
        "cli_agents": {
            "echo": {
                "cmd": [PY, "-c", f"import sys; print('{prefix}: ' + sys.argv[1])", "{prompt}"],
                "parse": "text",
            },
            "echo2": {
                "cmd": [PY, "-c", "import sys; print('TWO: ' + sys.argv[1])", "{prompt}"],
            },
        },
        "cli_fusion": {"default_cli": "echo"},
    }


async def _collect(gen):
    chunks = []
    async for c in gen:
        chunks.append(c)
    return chunks


def _final_content(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


# --------------------------------------------------------------------------- #
# Support helpers
# --------------------------------------------------------------------------- #

def test_render_prompt_single():
    assert support.render_prompt([{"role": "user", "content": "hi"}]) == "hi"


def test_render_prompt_multiturn_transcript():
    out = support.render_prompt(
        [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert "SYSTEM: be terse" in out and "USER: hello" in out


def test_select_single_cli_priority():
    cfg = _echo_config()
    reg = CliAdapterRegistry.from_config(cfg)
    # per-request param wins
    assert support.select_single_cli(cfg, {"cli": "echo2"}, reg) == "echo2"
    # else config default
    assert support.select_single_cli(cfg, {}, reg) == "echo"


def test_select_single_cli_none_when_empty():
    reg = CliAdapterRegistry.from_config({})
    assert support.select_single_cli({}, {}, reg) is None


# --------------------------------------------------------------------------- #
# Blueprint end-to-end (real subprocess)
# --------------------------------------------------------------------------- #

async def test_blueprint_runs_default_cli():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "ECHO: ping"
    # last chunk marked final
    assert chunks[-1].get("final") is True


async def test_blueprint_respects_cli_param():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    bp.set_params({"cli": "echo2"})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "TWO: ping"


def test_apply_skill_to_prompt_helper():
    # No skill → unchanged. Known bundled skill → instructions prepended.
    assert support.apply_skill_to_prompt("do x", {}) == ("do x", None)
    prompt, name = support.apply_skill_to_prompt("do x", {"skill": "conventional-commit"})
    assert name == "conventional-commit"
    assert "Conventional Commit" in prompt and prompt.rstrip().endswith("do x")
    # Unknown skill → unchanged, name None (caller warns).
    assert support.apply_skill_to_prompt("do x", {"skill": "nope-not-real"}) == ("do x", None)


async def test_blueprint_applies_skill_param():
    # echo prints the rendered prompt, so the injected skill text is observable.
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    bp.set_params({"cli": "echo", "skill": "conventional-commit"})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    final = _final_content(chunks)
    assert "Conventional Commit" in final and final.rstrip().endswith("ping")
    assert any("Applying skill `conventional-commit`" in str(c) for c in chunks)


async def test_blueprint_unknown_skill_warns_and_runs_bare():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    bp.set_params({"cli": "echo", "skill": "nope-not-real"})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "ECHO: ping"  # ran bare, no skill text
    assert any("not found" in str(c) for c in chunks)


def _traited_config() -> dict:
    # Two always-available echo agents with opposite capability traits.
    return {
        "cli_agents": {
            "brainy": {
                "cmd": [PY, "-c", "import sys; print('BRAINY: ' + sys.argv[1])", "{prompt}"],
                "parse": "text",
                "traits": {"intelligence": 0.95, "speed": 0.2, "cost": 0.2},
            },
            "speedy": {
                "cmd": [PY, "-c", "import sys; print('SPEEDY: ' + sys.argv[1])", "{prompt}"],
                "parse": "text",
                "traits": {"intelligence": 0.3, "speed": 0.95, "cost": 0.95},
            },
        }
    }


async def test_blueprint_selects_cli_by_profile_param():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_traited_config())
    bp.set_params({"profile": {"intelligence": 1, "speed": 0, "cost": 0}, "failover": False})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert _final_content(chunks) == "BRAINY: x"

    bp.set_params({"profile": {"intelligence": 0, "speed": 1, "cost": 1}, "failover": False})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert _final_content(chunks) == "SPEEDY: x"


def _per_model_config() -> dict:
    # One provider with two declared models carrying opposite traits.
    return {
        "cli_agents": {
            "gem": {
                "cmd": [PY, "-c", "import sys; print('GEM: ' + sys.argv[1])", "{prompt}"],
                "parse": "text",
                "traits": {"intelligence": 0.6, "speed": 0.95, "cost": 0.92},
                "models": {
                    "pro": {"traits": {"intelligence": 0.95, "speed": 0.30, "cost": 0.20}},
                    "flash": {"traits": {"intelligence": 0.60, "speed": 0.95, "cost": 0.92}},
                },
            }
        }
    }


def test_resolve_profile_candidate_picks_per_model():
    cfg = _per_model_config()
    reg = support.build_registry(cfg)
    # deep reasoning -> the pro model (per-model override beats provider default)
    assert support.resolve_profile_candidate({"intelligence": 1.0}, cfg, reg) == ("gem", "pro")
    # fast/cheap -> provider/flash granularity (same traits); cli is gem either way
    cli, _model = support.resolve_profile_candidate({"speed": 1.0, "cost": 1.0}, cfg, reg)
    assert cli == "gem"


def test_split_candidate():
    assert support.split_candidate("gemini@pro") == ("gemini", "pro")
    assert support.split_candidate("grok") == ("grok", None)


async def test_blueprint_announces_resolved_model():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_per_model_config())
    bp.set_params({"profile": {"intelligence": 1.0}, "failover": False})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    # ran the resolved provider and announced the per-model pick
    assert _final_content(chunks) == "GEM: x"
    assert any("model `pro`" in str(c) for c in chunks)


async def test_default_cli_outranks_profile():
    # An explicit default_cli is a deliberate global choice; it beats a profile.
    cfg = _traited_config()
    cfg["cli_fusion"] = {"default_cli": "speedy"}
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"profile": {"intelligence": 1.0}, "failover": False})  # would pick brainy
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert _final_content(chunks) == "SPEEDY: x"


async def test_explicit_cli_param_overrides_profile():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_traited_config())
    # Profile wants intelligence (brainy) but an explicit cli wins.
    bp.set_params({"cli": "speedy", "profile": {"intelligence": 1}, "failover": False})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert _final_content(chunks) == "SPEEDY: x"


async def test_blueprint_metadata_profile_drives_selection(monkeypatch):
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_traited_config())
    # A blueprint that *declares* it wants fast/cheap inference in its metadata.
    monkeypatch.setitem(bp.metadata, "inference_profile", {"intelligence": 0, "speed": 1, "cost": 1})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert _final_content(chunks) == "SPEEDY: x"


async def test_blueprint_stages_skill_assets_into_workdir(tmp_path):
    # The bundled counting-lines skill ships count.py; running with a workdir
    # must stage it so a write-mode CLI could execute it.
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    bp.set_params({"cli": "echo", "skill": "counting-lines", "workdir": str(tmp_path)})
    await _collect(bp.run([{"role": "user", "content": "count lines in foo.txt"}]))
    assert (tmp_path / "count.py").is_file()


async def test_blueprint_no_agents_configured():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config={})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert "No CLI agents are configured" in _final_content(chunks)


async def test_blueprint_empty_prompt():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_echo_config())
    chunks = await _collect(bp.run([]))
    assert "No prompt provided" in _final_content(chunks)


async def test_blueprint_reports_cli_failure():
    cfg = {
        "cli_agents": {
            "boom": {"cmd": [PY, "-c", "import sys; sys.exit(2)", "{prompt}"]},
        },
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert "failed" in _final_content(chunks)


# --------------------------------------------------------------------------- #
# Streaming (stream=True)
# --------------------------------------------------------------------------- #

def _message_contents(chunks):
    return [
        c["messages"][0]["content"]
        for c in chunks
        if isinstance(c, dict) and c.get("messages") and c["messages"][0].get("content") is not None
    ]


def _stream_config():
    code = "import sys; sys.stdout.write('line1\\nline2\\n')"
    return {
        "cli_agents": {"s": {"cmd": [PY, "-c", code, "{prompt}"], "parse": "text"}},
        "cli_fusion": {"default_cli": "s"},
    }


async def test_blueprint_streams_deltas_without_duplication():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_stream_config())
    chunks = await _collect(bp.run([{"role": "user", "content": "go"}], stream=True))
    # The concatenated deltas reproduce the output exactly — no final full resend.
    assert "".join(_message_contents(chunks)) == "line1\nline2\n"


async def test_blueprint_non_streaming_still_single_full_message():
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=_stream_config())
    chunks = await _collect(bp.run([{"role": "user", "content": "go"}], stream=False))
    # Non-streaming yields exactly one content message (the full answer).
    assert _message_contents(chunks) == ["line1\nline2"]
    assert chunks[-1].get("final") is True


async def test_blueprint_streaming_reports_failure():
    cfg = {
        "cli_agents": {"boom": {"cmd": [PY, "-c", "import sys; sys.exit(2)", "{prompt}"]}},
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}], stream=True))
    assert "failed" in _final_content(chunks)


async def test_blueprint_streaming_json_adapter_falls_back_to_oneshot():
    code = "print('{\"result\": \"answer\"}')"
    cfg = {
        "cli_agents": {"j": {"cmd": [PY, "-c", code, "{prompt}"], "parse": "json:.result"}},
        "cli_fusion": {"default_cli": "j"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}], stream=True))
    # json: can't stream incrementally -> one-shot fallback returns the parsed value.
    assert _final_content(chunks) == "answer"


# --------------------------------------------------------------------------- #
# Failover (single-agent resilience to broken/missing CLIs)
# --------------------------------------------------------------------------- #

def _boom(code: int = 1) -> dict:
    return {"cmd": [PY, "-c", f"import sys; sys.exit({code})", "{prompt}"]}


def _ok(prefix: str) -> dict:
    return {"cmd": [PY, "-c", f"import sys; print('{prefix}: ' + sys.argv[1])", "{prompt}"]}


async def test_failover_primary_fails_uses_explicit_fallback():
    cfg = {
        "cli_agents": {"boom": _boom(), "backup": _ok("BACKUP")},
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"cli": "boom", "fallback": ["backup"]})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "BACKUP: ping"


async def test_failover_auto_uses_other_available_when_primary_fails():
    # No explicit fallback -> auto-failover to other available adapters.
    cfg = {
        "cli_agents": {"boom": _boom(), "good": _ok("GOOD")},
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "GOOD: ping"


async def test_failover_primary_success_does_not_fall_over():
    cfg = {
        "cli_agents": {"primary": _ok("PRIMARY"), "backup": _ok("BACKUP")},
        "cli_fusion": {"default_cli": "primary"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "PRIMARY: ping"


async def test_failover_all_candidates_fail_reports_cleanly():
    cfg = {
        "cli_agents": {"boom1": _boom(), "boom2": _boom(2)},
        "cli_fusion": {"default_cli": "boom1"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"cli": "boom1", "fallback": ["boom2"]})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert "failed" in _final_content(chunks).lower()


async def test_failover_disabled_is_strict_single_cli():
    cfg = {
        "cli_agents": {"boom": _boom(), "good": _ok("GOOD")},
        "cli_fusion": {"default_cli": "boom"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"cli": "boom", "failover": False})
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    # Strict: it fails on the primary and does NOT silently switch models.
    assert "GOOD" not in _final_content(chunks)
    assert "failed" in _final_content(chunks).lower()


async def test_failover_skips_not_installed_primary():
    cfg = {
        "cli_agents": {
            "ghost": {"cmd": ["definitely-not-a-real-cli-zzz", "{prompt}"]},
            "real": _ok("REAL"),
        },
        "cli_fusion": {"default_cli": "ghost"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "REAL: ping"


def test_resolve_failover_chain_orders_and_dedups():
    cfg = {"cli_agents": {"a": _ok("A"), "b": _ok("B"), "c": _ok("C")}}
    reg = CliAdapterRegistry.from_config(cfg)
    # explicit primary + fallback, deduped, order preserved
    chain = support.resolve_failover_chain(cfg, {"cli": "a", "fallback": ["b", "a", "c"]}, reg)
    assert chain == ["a", "b", "c"]
    # failover disabled -> primary only
    assert support.resolve_failover_chain(cfg, {"cli": "a", "failover": False}, reg) == ["a"]


# --------------------------------------------------------------------------- #
# Consensus agents — designate an agent to run a panel instead of one call
# --------------------------------------------------------------------------- #

def _ag(prefix: str, **over) -> dict:
    base = {"cmd": [PY, "-c", f"import sys; print('{prefix}:' + sys.argv[1])", "{prompt}"]}
    base.update(over)
    return base


def _progress_text(chunks):
    return "\n".join(
        c["content"] for c in chunks if isinstance(c, dict) and c.get("type") == "fusion_progress"
    )


def test_resolve_consensus_true_panels_real_clis_only():
    reg = CliAdapterRegistry.from_config(
        {"cli_agents": {"meta": _ag("M", consensus=True), "a": _ag("A"), "b": _ag("B")}}
    )
    panel, judge = support.resolve_agent_consensus(reg.get("meta").config, reg)
    assert set(panel) == {"a", "b"}  # default = real CLIs, not the meta agent
    assert "meta" not in panel
    assert judge in ("a", "b")


def test_resolve_consensus_whitelist_prefers_available():
    reg = CliAdapterRegistry.from_config(
        {"cli_agents": {"a": _ag("A", consensus=["b"]), "b": _ag("B")}}
    )
    panel, _ = support.resolve_agent_consensus(reg.get("a").config, reg)
    assert panel == ["b"]


def test_resolve_consensus_whitelist_no_match_falls_back_to_default():
    reg = CliAdapterRegistry.from_config(
        {"cli_agents": {"meta": _ag("M", consensus=["ghost", "nope"]), "a": _ag("A"), "b": _ag("B")}}
    )
    panel, _ = support.resolve_agent_consensus(reg.get("meta").config, reg)
    assert set(panel) == {"a", "b"}  # whitelist matched nothing -> default (real CLIs)


def test_resolve_consensus_none_when_not_designated():
    reg = CliAdapterRegistry.from_config({"cli_agents": {"a": _ag("A")}})
    assert support.resolve_agent_consensus(reg.get("a").config, reg) is None


async def test_consensus_agent_runs_panel_with_judge():
    judge_cfg = {"cmd": [PY, "-c", "print('{\"answer\": \"CONSENSUS\", \"done\": true}')", "{prompt}"], "parse": "text"}
    cfg = {
        "cli_agents": {
            "lead": _ag("LEAD", consensus={"panel": ["a", "b"], "judge": "judge"}),
            "a": _ag("A"),
            "b": _ag("B"),
            "judge": judge_cfg,
        },
        "cli_fusion": {"default_cli": "lead"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    assert _final_content(chunks) == "CONSENSUS"
    assert "consensus agent" in _progress_text(chunks)


async def test_non_consensus_agent_is_still_single_call():
    cfg = {"cli_agents": {"solo": _ag("SOLO")}, "cli_fusion": {"default_cli": "solo"}}
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "SOLO:ping"
    assert "consensus agent" not in _progress_text(chunks)


def test_resolve_consensus_int_is_self_consensus():
    reg = CliAdapterRegistry.from_config({"cli_agents": {"coder": _ag("C")}})
    panel, judge = support.resolve_consensus_spec(3, "coder", reg)
    assert panel == ["coder", "coder", "coder"]  # same persona x3
    assert judge == "coder"


def test_resolve_consensus_int_below_two_is_single():
    reg = CliAdapterRegistry.from_config({"cli_agents": {"coder": _ag("C")}})
    assert support.resolve_consensus_spec(1, "coder", reg) is None


async def test_param_consensus_self_consensus_runs_n():
    cfg = {"cli_agents": {"coder": _ag("SOLO")}, "cli_fusion": {"default_cli": "coder"}}
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"consensus": 3})
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    assert _final_content(chunks) == "SOLO:q"  # 3 identical samples -> that answer
    assert "consensus agent" in _progress_text(chunks)


async def test_param_consensus_overrides_config_to_single():
    cfg = {
        "cli_agents": {"coder": _ag("SOLO", consensus=True), "b": _ag("B")},
        "cli_fusion": {"default_cli": "coder"},
    }
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"cli": "coder", "consensus": False})  # force single despite config
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    assert _final_content(chunks) == "SOLO:ping"
    assert "consensus agent" not in _progress_text(chunks)
