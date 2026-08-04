"""Isolate MCP provider tests from real blueprint discovery state."""
import pytest


@pytest.fixture(autouse=True)
def clear_blueprint_extra_dirs(monkeypatch):
    """Prevent real user blueprint dirs from leaking into provider tests."""
    import swarm.mcp.provider as prov
    monkeypatch.setattr(prov, "BLUEPRINT_EXTRA_DIRS", [])
