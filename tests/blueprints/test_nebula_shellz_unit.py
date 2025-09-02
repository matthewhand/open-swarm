import sys
import types
import importlib
import os

import pytest


def _inject_stubbed_modules():
    """Stub heavy external deps so the blueprint module can import."""
    # Create minimal module objects
    stubs = {}

    # agents core
    agents_mod = types.ModuleType("agents")
    agents_mcp_mod = types.ModuleType("agents.mcp")
    agents_models_mod = types.ModuleType("agents.models")
    agents_models_interface_mod = types.ModuleType("agents.models.interface")
    agents_models_openai_mod = types.ModuleType("agents.models.openai_chatcompletions")

    class _DummyModel:  # noqa: D401 - minimal placeholder
        """Placeholder for Model interface."""

    class _DummyOpenAIModel:  # noqa: D401 - minimal placeholder
        """Placeholder for OpenAIChatCompletionsModel."""

        def __init__(self, *_, **__):
            pass

    class _DummyAgent:
        def __init__(self, *_, **__):
            pass

        def as_tool(self, *_, **__):
            def _tool(*a, **k):
                return None

            return _tool

    def _function_tool(fn):
        return fn

    # Populate attributes
    agents_mod.Agent = _DummyAgent
    agents_mod.Tool = object
    agents_mod.function_tool = _function_tool
    agents_mcp_mod.MCPServer = object
    agents_models_interface_mod.Model = _DummyModel
    agents_models_openai_mod.OpenAIChatCompletionsModel = _DummyOpenAIModel

    # openai client stub
    openai_mod = types.ModuleType("openai")

    class _DummyAsyncOpenAI:
        def __init__(self, *_, **__):
            pass

    openai_mod.AsyncOpenAI = _DummyAsyncOpenAI

    # rich stubs
    rich_panel_mod = types.ModuleType("rich.panel")

    class _DummyPanel:
        def __init__(self, *_, **__):
            pass

    rich_panel_mod.Panel = _DummyPanel

    # blueprint base + ux
    swarm_core_blueprint_base = types.ModuleType("swarm.core.blueprint_base")
    swarm_core_blueprint_ux = types.ModuleType("swarm.core.blueprint_ux")

    class _DummyBlueprintBase:
        def __init__(self, *_, **__):
            pass

        def get_llm_profile(self, *_):
            return {"provider": "openai", "model": "gpt-mock"}

        @property
        def config(self):
            return {"llm_profile": "default"}

    class _DummyUX:
        def __init__(self, *_, **__):
            pass

        def spinner(self, *_a, **_k):
            return "[SPINNER] Generating..."

        def summary(self, *_a, **_k):
            return "Summary"

        def ansi_emoji_box(self, *_, **__):
            return "[BOX] Content"

    swarm_core_blueprint_base.BlueprintBase = _DummyBlueprintBase
    swarm_core_blueprint_ux.BlueprintUXImproved = _DummyUX

    # Register in sys.modules
    stubs.update(
        {
            "agents": agents_mod,
            "agents.mcp": agents_mcp_mod,
            "agents.models": agents_models_mod,
            "agents.models.interface": agents_models_interface_mod,
            "agents.models.openai_chatcompletions": agents_models_openai_mod,
            "openai": openai_mod,
            "rich.panel": rich_panel_mod,
            "swarm.core.blueprint_base": swarm_core_blueprint_base,
            "swarm.core.blueprint_ux": swarm_core_blueprint_ux,
        }
    )

    for name, mod in stubs.items():
        sys.modules.setdefault(name, mod)


@pytest.fixture(scope="module", autouse=True)
def stub_heavy_deps():
    """Ensure imports in blueprint module succeed during tests."""
    _inject_stubbed_modules()
    # Reload module if already imported in other tests
    sys.modules.pop(
        "src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz", None
    )
    yield
    # Do not clean up stubs to avoid affecting other tests that may rely on them.


def test_execute_shell_command_raw_handles_empty_command():
    mod = importlib.import_module(
        "src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz"
    )
    out = mod._execute_shell_command_raw("")
    assert "No command provided" in out


def test_execute_shell_command_raw_success_echo():
    mod = importlib.import_module(
        "src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz"
    )
    out = mod._execute_shell_command_raw("echo hello")
    assert "Exit Code: 0" in out
    assert "STDOUT" in out and "hello" in out


def test_execute_shell_command_raw_not_found():
    mod = importlib.import_module(
        "src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz"
    )
    # Use an obviously-invalid command name
    out = mod._execute_shell_command_raw("__definitely_missing_command__ --flag")
    # Accept either a formatted error message or a standard shell 127 exit handling
    assert ("Error:" in out) or ("Exit Code:" in out)
    # If stderr is available, it often contains 'not found' wording
    # but do not require it strictly across OS/shells.


def test_timeout_is_configurable(monkeypatch):
    mod = importlib.import_module(
        "src.swarm.blueprints.nebula_shellz.blueprint_nebula_shellz"
    )
    # Force a very small timeout and a command that sleeps slightly longer
    monkeypatch.setenv("SWARM_COMMAND_TIMEOUT", "1")
    # Use a portable Python sleep to avoid shell differences
    py_sleep = f"{sys.executable} -c 'import time; time.sleep(2)'"
    out = mod._execute_shell_command_raw(py_sleep)
    assert "timed out" in out.lower()
