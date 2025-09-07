import logging
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from agents.mcp import MCPServer
from swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot import (
    WhiskeyTangoFoxtrotBlueprint,
)

SQLITE_MODULE_PATH = 'swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot.SQLITE_DB_PATH'
logger = logging.getLogger(__name__)

@pytest.fixture
def temporary_db_wtf(tmp_path):
    db_file = tmp_path / "test_wtf_services.db"
    if db_file.exists():
        db_file.unlink()
    return db_file

@pytest.fixture
def wtf_blueprint_instance(temporary_db_wtf):
    with patch(SQLITE_MODULE_PATH, new=temporary_db_wtf):
        with patch('swarm.core.blueprint_base.BlueprintBase._load_configuration', return_value=None):
            with patch('swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot.WhiskeyTangoFoxtrotBlueprint._get_model_instance') as mock_get_model:
                mock_model_instance = MagicMock(name="MockModelInstance")
                mock_get_model.return_value = mock_model_instance

                instance = WhiskeyTangoFoxtrotBlueprint(blueprint_id="test_wtf", config_path="dummy_path_for_test.json")
                instance._config = {
                    'llm': {'default': {'provider': 'mock', 'model': 'mock-model'}},
                    'mcpServers': {},
                    'settings': {'default_llm_profile': 'default'},
                    'blueprints': {getattr(instance, 'blueprint_id', 'test_wtf'): {}}
                }
                instance._raw_config = instance._config.copy()
                yield instance

def test_wtf_agent_creation(wtf_blueprint_instance):
    blueprint = wtf_blueprint_instance
    logger.debug(f"test_wtf_agent_creation: Blueprint _config: {blueprint._config if hasattr(blueprint, '_config') else 'MISSING'}")
    assert hasattr(blueprint, '_config') and blueprint._config is not None, "Pre-condition failed: blueprint._config is not set."

    mock_mcps = [
        MagicMock(spec=MCPServer, name="sqlite"), MagicMock(spec=MCPServer, name="brave-search"),
        MagicMock(spec=MCPServer, name="mcp-npx-fetch"), MagicMock(spec=MCPServer, name="mcp-doc-forge"),
        MagicMock(spec=MCPServer, name="filesystem"),
    ]
    for mcp_mock in mock_mcps: mcp_mock.get_tools = MagicMock(return_value=[])

    starting_agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)
    assert starting_agent is not None
    assert starting_agent.name == "Valory"

def test_wtf_db_initialization(wtf_blueprint_instance, temporary_db_wtf):
    blueprint = wtf_blueprint_instance
    # Ensure _config is present for initialize_db if it relies on it (it doesn't directly, but create_starting_agent does)
    assert hasattr(blueprint, '_config') and blueprint._config is not None, "Pre-condition failed: blueprint._config is not set for DB initialization."

    blueprint.initialize_db()

    assert temporary_db_wtf.exists(), "Database file was not created"
    conn = sqlite3.connect(temporary_db_wtf)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services';")
    assert cursor.fetchone() is not None, "'services' table not found in DB"
    conn.close()

def test_wtf_db_initialization_idempotent(wtf_blueprint_instance, temporary_db_wtf):
    blueprint = wtf_blueprint_instance
    # First initialization should create DB and schema
    blueprint.initialize_db()
    # Second initialization should be a no-op and not error
    blueprint.initialize_db()

    # Validate DB exists and schema remains correct
    assert temporary_db_wtf.exists(), "Database file was not created after repeated initialization"
    conn = sqlite3.connect(temporary_db_wtf)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services';")
    assert cursor.fetchone() is not None, "'services' table not found after repeated initialization"
    # Ensure index declared in implementation exists as well
    cursor.execute("PRAGMA index_list('services');")
    indexes = [row[1] for row in cursor.fetchall()]  # row[1] is index name
    assert 'idx_services_name' in indexes, "Expected index 'idx_services_name' missing"
    conn.close()

def test_wtf_delegation_flow(wtf_blueprint_instance, monkeypatch):
    blueprint = wtf_blueprint_instance

    # Mock Runner.run to simulate a short delegation flow yielding a single message
    class _DummyGen:
        def __iter__(self):
            return self
        def __next__(self):
            raise StopIteration

    messages = [{"role": "user", "content": "Track new free tier services"}]

    def _fake_runner_run(_agent, _instruction):
        # First yield a message-like chunk, then stop
        yielded = False
        def _gen():
            nonlocal yielded
            if not yielded:
                yielded = True
                yield {"messages": [{"role": "assistant", "content": "Delegated: done"}]}
            return
            yield  # pragma: no cover
        return _gen()

    monkeypatch.setattr(
        "swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot.Runner.run",
        _fake_runner_run,
    )

    # Collect async generator output
    out = []
    async def _collect():
        async for chunk in blueprint.run(messages, mcp_servers_override=[]):
            out.append(chunk)

    import asyncio
    asyncio.run(_collect())

    # Ensure at least one assistant message was surfaced from the delegation
    assert any(
        isinstance(c, dict)
        and isinstance(c.get("messages"), list)
        and c["messages"]
        and "Delegated: done" in c["messages"][0].get("content", "")
        for c in out
    ), "Expected a delegated message to be yielded from run()"

def test_wtf_run_yields_spinner_when_no_results(wtf_blueprint_instance, monkeypatch):
    blueprint = wtf_blueprint_instance

    # Force Runner.run to produce no chunks at all
    def _empty_runner_run(_agent, _instruction):
        if False:
            yield None  # pragma: no cover
        return iter(())

    monkeypatch.setattr(
        "swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot.Runner.run",
        _empty_runner_run,
    )

    messages = [{"role": "user", "content": "Any"}]

    out = []
    async def _collect():
        async for chunk in blueprint.run(messages, mcp_servers_override=[]):
            out.append(chunk)

    import asyncio
    asyncio.run(_collect())

    # When no result chunks are produced, implementation yields a spinner once
    assert any(
        isinstance(c, dict)
        and isinstance(c.get("messages"), list)
        and c["messages"]
        and isinstance(c["messages"][0].get("content", None), str)
        and "Processing" in c["messages"][0]["content"]
        for c in out
    ), "Expected a spinner message when no results are produced"
