"""hybrid_team per-step model routing.

ROLE_PROFILES maps a sub-task role to an inference_profile; via BlueprintBase's
scorer each role resolves to the closest tagged profile in the `llm` config.
We assert the routing with a controlled config (so the picks are unambiguous)
rather than depending on swarm_config.json's exact tuning.
"""
from __future__ import annotations

from swarm.blueprints.hybrid_team.blueprint_hybrid_team import HybridTeamBlueprint

CONFIG = {
    "llm": {
        "default": {"provider": "openai", "model": "d"},  # untagged -> not scorable
        "brainy": {"provider": "openai", "model": "b", "intelligence": 0.95, "speed": 0.2, "cost": 0.2},
        "mid": {"provider": "openai", "model": "m", "intelligence": 0.6, "speed": 0.6, "cost": 0.6},
        "cheap": {"provider": "openai", "model": "c", "intelligence": 0.2, "speed": 0.95, "cost": 0.95},
    }
}


def _resolved_for_role(role: str) -> str:
    bp = HybridTeamBlueprint(config=CONFIG)
    bp._inference_profile = HybridTeamBlueprint.ROLE_PROFILES[role]
    if hasattr(bp, "_resolved_llm_profile"):
        del bp._resolved_llm_profile
    return bp._resolve_llm_profile()


def test_orchestration_routes_to_smartest():
    assert _resolved_for_role("orchestration") == "brainy"


def test_agent_routes_to_balanced():
    assert _resolved_for_role("agent") == "mid"


def test_auxiliary_routes_to_cheap_fast():
    assert _resolved_for_role("auxiliary") == "cheap"


def test_role_profiles_cover_expected_roles():
    assert set(HybridTeamBlueprint.ROLE_PROFILES) == {"orchestration", "agent", "auxiliary"}


def test_metadata_inference_profile_reflects_mixed_nature():
    ip = HybridTeamBlueprint.metadata["inference_profile"]
    # mixed coordinator + execution: capable but not maxed, with speed weight
    assert ip["intelligence"] < 0.95 and "speed" in ip
