import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.poets.blueprint_poets import PoetsBlueprint
# from agents import Agent, Runner, RunResult, MCPServer

# Use the same DB path logic as the blueprint
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(".") / DB_FILE_NAME

@pytest.fixture(scope="function")
def temporary_db_poets():
    """Creates a temporary, empty SQLite DB for testing Poets."""
    test_db_path = Path("./test_swarm_instructions_poets.db")
    if test_db_path.exists():
        test_db_path.unlink()
    yield test_db_path
    if test_db_path.exists():
        test_db_path.unlink()

@pytest.fixture
def poets_blueprint_instance():
    with patch('swarm.core.blueprint_base.BlueprintBase._load_and_process_config', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model_instance = MagicMock()
            mock_get_model.return_value = mock_model_instance
            from swarm.blueprints.poets.blueprint_poets import PoetsBlueprint
            # Patch abstract methods to allow instantiation
            PoetsBlueprint.__abstractmethods__ = set()
            instance = PoetsBlueprint(blueprint_id="test_poets", debug=True)
            instance._config = {'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}
            instance.mcp_server_configs = {}
            return instance

@pytest.mark.skip(reason="SQLite interaction testing needs refinement.")
@patch('blueprints.poets.blueprint_poets.DB_PATH', new_callable=lambda: Path("./test_swarm_instructions_poets.db"))
@patch('blueprints.poets.blueprint_poets.BlueprintBase._load_configuration', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}})
@patch('blueprints.poets.blueprint_poets.BlueprintBase._get_model_instance')
def test_poets_db_initialization(mock_get_model, mock_load_config, temporary_db_poets):
    """Test if the DB table is created and Poets sample data loaded."""
    from blueprints.poets.blueprint_poets import PoetsBlueprint

    blueprint = PoetsBlueprint(debug=True)
    blueprint._init_db_and_load_data() # Call directly

    assert temporary_db_poets.exists()
    with sqlite3.connect(temporary_db_poets) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_instructions';")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT COUNT(*) FROM agent_instructions WHERE agent_name = ?", ("Gritty Buk",))
        assert cursor.fetchone()[0] > 0

def test_poets_agent_creation(poets_blueprint_instance):
    """Test if Poets agent is created correctly."""
    blueprint = poets_blueprint_instance
    m1 = MagicMock(); m1.name = "memory"
    m2 = MagicMock(); m2.name = "filesystem"
    m3 = MagicMock(); m3.name = "mcp-shell"
    mock_mcp_list = [m1, m2, m3]
    agent = blueprint.create_starting_agent(mcp_servers=mock_mcp_list)
    assert agent is not None
    valid_poets = [
        "Raven Poe", "Mystic Blake", "Bard Whit", "Echo Plath", "Frosted Woods",
        "Harlem Lang", "Verse Neru", "Haiku Bash"
    ]
    assert agent.name in valid_poets

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_poets_collaboration_flow(temporary_db_poets):
    """Test a hypothetical multi-agent handoff sequence."""
    # Needs Runner mocking, DB mocking/setup.
    assert False

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_poets_cli_execution():
    """Test running the blueprint via CLI."""
    # Needs subprocess testing or mocks.
    assert False
