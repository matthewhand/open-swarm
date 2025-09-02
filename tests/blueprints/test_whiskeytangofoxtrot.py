import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sqlite3
import os
import logging

from swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot import WhiskeyTangoFoxtrotBlueprint
from agents.mcp import MCPServer
from agents import Agent 

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
        with patch('swarm.core.blueprint_base.BlueprintBase._load_configuration', return_value=None) as mock_load_config:
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

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
def test_wtf_delegation_flow(wtf_blueprint_instance): pass

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_wtf_cli_execution(): pass
