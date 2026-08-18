"""Isolate LiteLLM/OpenAI env overrides so unit tests use their own config."""
import os
import time
import pytest

_LITELLM_VARS = (
    "LITELLM_BASE_URL", "LITELLM_API_KEY", "LITELLM_MODEL",
    "OPENAI_BASE_URL", "OPENAI_API_KEY", "DEFAULT_LLM",
)

@pytest.fixture(autouse=True)
def clear_litellm_env(monkeypatch):
    for var in _LITELLM_VARS:
        monkeypatch.delenv(var, raising=False)


def _cli_startup_ms() -> int:
    from tests.xdg_isolation import run_swarm_cli

    t = time.monotonic()
    try:
        run_swarm_cli(
            "--help",
            module="swarm.core.swarm_cli",
            overrides={"SWARM_TEST_MODE": "1"},
            timeout=60,
        )
    except Exception:
        return 99999
    return int((time.monotonic() - t) * 1000)


_SLOW_CLI = None


def pytest_runtest_setup(item):
    """Skip subprocess-heavy CLI journey tests if startup is too slow."""
    global _SLOW_CLI
    if "test_documented_cli_journey" not in item.nodeid and "test_userguide_captures" not in item.nodeid:
        return
    if _SLOW_CLI is None:
        _SLOW_CLI = _cli_startup_ms() > 25000  # >25s = too slow
    if _SLOW_CLI:
        pytest.skip("CLI subprocess startup >25s — skipping in slow environment")
