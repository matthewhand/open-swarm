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
        # Patch _load_configuration on BlueprintBase.
        # The WTFBlueprint.__init__ will call super().__init__(blueprint_id),
        # then it will call self._load_configuration(config_path, **kwargs) itself.
        # This second call is what we want our side_effect to respond to for setting _config.
        with patch('swarm.core.blueprint_base.BlueprintBase._load_configuration') as mock_load_config:
            
            def side_effect_for_manual_call(self_instance, config_path_arg, **kwargs_arg):
                # This side_effect is for the WTFBlueprint's *direct call* to self._load_configuration.
                # self_instance here will be the WTFBlueprint instance.
                logger.debug(f"wtf_fixture: side_effect_for_manual_call on {type(self_instance)} with config_path='{config_path_arg}', kwargs={kwargs_arg}")
                self_instance._config = {
                    'llm': {'default': {'provider': 'mock', 'model': 'mock-model'}},
                    'mcpServers': {}, 
                    'settings': {'default_llm_profile': 'default'},
                    'blueprints': {getattr(self_instance, 'blueprint_id', 'test_wtf'): {}}
                }
                self_instance._raw_config = self_instance._config.copy()
                logger.debug(f"wtf_fixture: {type(self_instance)}._config set to {self_instance._config}")

            mock_load_config.side_effect = side_effect_for_manual_call
            
            with patch('swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot.WhiskeyTangoFoxtrotBlueprint._get_model_instance') as mock_get_model:
                mock_model_instance = MagicMock(name="MockModelInstance")
                mock_get_model.return_value = mock_model_instance
                
                # When WTFBlueprint is instantiated, its __init__ will first call super().__init__(blueprint_id).
                # If BlueprintUXImproved calls super().__init__(blueprint_id) which hits BlueprintBase.__init__(blueprint_id),
                # BlueprintBase.__init__ will call self._load_configuration() (with no args other than self).
                # This first call to the mock might not be what we want to set the config.
                # The *second* call from WTFBlueprint's __init__ (self._load_configuration(config_path, **kwargs))
                # is the one our side_effect is tailored for.
                # To handle the first call (if it happens and if it's different):
                # We can make the side_effect more robust or assume the test focuses on the manual call.
                # For simplicity, let's assume the manual call is the primary one that sets config for the test.

                instance = WhiskeyTangoFoxtrotBlueprint(blueprint_id="test_wtf", config_path="dummy_path_for_test.json")
                
                # Check if _config was set by the mock
                assert hasattr(instance, '_config') and instance._config is not None, \
                    "Fixture error: instance._config was not set by mocked _load_configuration"
                logger.debug(f"wtf_fixture: Blueprint instance created, _config: {instance._config}")
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

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
def test_wtf_delegation_flow(wtf_blueprint_instance): pass

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_wtf_cli_execution(): pass
