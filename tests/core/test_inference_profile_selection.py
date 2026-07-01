"""Integration of inference_profile scoring into BlueprintBase LLM selection.

Covers the new behaviour added in feat/smart-llm-routing: a blueprint declares a
desired ``inference_profile`` (a suggestion), and the framework scores it against
the *tagged* profiles in the config ``llm`` section via inference_profile.resolve.
Explicit profile names in config take priority over inference suggestions.
"""
from unittest.mock import patch

from swarm.core.blueprint_base import BlueprintBase


class _BP(BlueprintBase):
    async def run(self, messages, **kwargs):  # pragma: no cover - not exercised
        yield {"messages": [{"role": "assistant", "content": "ok"}]}

    @property
    def metadata(self):
        return getattr(self, "_test_metadata", {"title": "t", "description": "d"})


CONFIG = {
    "llm": {
        # untagged -> never a scorable candidate
        "default": {"provider": "openai", "model": "d", "api_key": "k"},
        "smart": {"provider": "openai", "model": "s", "intelligence": 0.9, "speed": 0.3, "cost": 0.2},
        "fast": {"provider": "openai", "model": "f", "intelligence": 0.2, "speed": 0.9, "cost": 0.9},
    },
    "blueprints": {},
}


def _bp(metadata=None, **kw):
    bp = _BP("bp", config=CONFIG, **kw)
    if metadata is not None:
        bp._test_metadata = metadata
    return bp


def test_candidates_only_include_tagged_profiles():
    bp = _bp()
    assert set(bp._llm_candidates()) == {"smart", "fast"}


def test_high_intelligence_picks_smart():
    bp = _bp(metadata={"inference_profile": {"intelligence": 1.0}})
    assert bp._resolve_llm_profile() == "smart"


def test_fast_and_cheap_picks_fast():
    bp = _bp(metadata={"inference_profile": {"speed": 0.9, "cost": 0.9}})
    assert bp._resolve_llm_profile() == "fast"


def test_explicit_profile_name_beats_suggestion():
    cfg = dict(CONFIG, llm_profile="default")
    bp = _BP("bp", config=cfg)
    bp._test_metadata = {"inference_profile": {"intelligence": 1.0}}
    assert bp._resolve_llm_profile() == "default"


def test_env_vars_do_not_override_inference():
    """DEFAULT_LLM / LITELLM_MODEL no longer act as escape hatches."""
    bp = _bp(metadata={"inference_profile": {"intelligence": 1.0}})
    with patch.dict("os.environ", {"DEFAULT_LLM": "fast", "LITELLM_MODEL": "something"}):
        # Should still pick based on inference (smart has highest intelligence), not env
        assert bp._resolve_llm_profile() == "smart"


def test_no_axis_suggestion_falls_through_to_default():
    # An empty / axis-less suggestion is undecidable -> normal default.
    bp = _bp(metadata={"inference_profile": {}})
    assert bp._resolve_llm_profile() == "default"


def test_no_suggestion_falls_through_to_default():
    bp = _bp(metadata={"title": "t"})
    assert bp._resolve_llm_profile() == "default"


def test_make_agent_param_overrides_metadata_suggestion():
    bp = _bp(metadata={"inference_profile": {"intelligence": 1.0}})  # would pick 'smart'
    # Programmatic suggestion (as make_agent would set) wins and re-resolves.
    bp._inference_profile = {"speed": 0.9, "cost": 0.9}
    if hasattr(bp, "_resolved_llm_profile"):
        del bp._resolved_llm_profile
    assert bp._resolve_llm_profile() == "fast"


def test_pure_env_bootstrap_plus_inference_scoring(monkeypatch, tmp_path):
    """Dedicated test for pure-env bootstrap + inference scoring.

    - No swarm_config.json (chdir + cleared search envs)
    - OPENAI_* env only (exercises get_openai_bootstrap synthesis of llm.default)
    - The synthesized default carries capability scores so inference_profile
      resolution can select it (the only tagged candidate).
    - Covers early AppConfig/CLI call sites indirectly via bootstrap path.
    """
    # Isolate filesystem/config search completely
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SWARM_CONFIG_PATH", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    # Prevent AppConfig path from supplying a config (would bypass synth)
    monkeypatch.setattr(
        "django.apps.apps.get_app_config",
        lambda name: (_ for _ in ()).throw(RuntimeError("no swarm appconfig in pure-env test")),
        raising=False,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "sk-pure-env-bootstrap")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://test-pure-env:9876/v1")

    # Passing no explicit config (i.e. default None) triggers the full load path + synth
    bp = _BP("pure_env_bp")
    llm_sec = bp._config.get("llm", {})
    assert "default" in llm_sec, "pure-env must synthesize llm.default"
    prof = llm_sec["default"]
    assert prof.get("api_key") == "sk-pure-env-bootstrap"
    assert prof.get("base_url") == "http://test-pure-env:9876/v1"
    assert prof.get("intelligence") == 0.6 and prof.get("speed") == 0.6
    assert "provider" in prof

    # Inference scoring path must function against the bootstrapped profile
    bp_inf = _BP("pure_env_bp_inf")
    bp_inf._test_metadata = {"inference_profile": {"intelligence": 0.55, "speed": 0.4}}
    # Only one tagged candidate ("default") -> it wins when axes requested
    resolved = bp_inf._resolve_llm_profile()
    assert resolved == "default"

    sel = bp_inf._select_profile_by_inference()
    assert sel == "default"
