"""Regression: django_chat must retain its loaded config / LLM profile.

The blueprint's __init__ previously re-assigned `self._config = config if config
is not None else None` (and nulled `_llm_profile_name`) AFTER the base __init__
had already loaded the config — so at runtime it reported "not configured" even
with a valid `llm` profile. These guard that it keeps the config.
"""

from __future__ import annotations

from swarm.blueprints.django_chat.blueprint_django_chat import DjangoChatBlueprint

_CFG = {
    "llm": {"default": {"provider": "openai", "model": "m", "base_url": "http://x/v1", "api_key": "k"}}
}


def test_init_does_not_null_passed_config():
    bp = DjangoChatBlueprint(config=_CFG)
    assert bp._config == _CFG  # not overwritten to None
    assert bp.get_llm_profile(bp.llm_profile_name).get("base_url") == "http://x/v1"


def test_unconfigured_degrades_gracefully():
    bp = DjangoChatBlueprint(config={})
    # No usable profile -> a clear message, never the old "Would respond to:" stub.
    import asyncio

    async def _collect():
        return [c async for c in bp.run([{"role": "user", "content": "hi"}])]

    chunks = asyncio.get_event_loop().run_until_complete(_collect())
    content = chunks[-1]["messages"][0]["content"]
    assert "not configured" in content
    assert "Would respond to" not in content
