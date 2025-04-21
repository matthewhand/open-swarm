import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.unapologetic_poets.blueprint_unapologetic_poets import UnapologeticPoetsBlueprint
# from agents import Agent, Runner, RunResult, MCPServer

# Use the same DB path logic as the blueprint
DB_FILE_NAME = "swarm_instructions.db"
DB_PATH = Path(".") / DB_FILE_NAME

@pytest.fixture(scope="function")
def temporary_db_upoets():
    """Creates a temporary, empty SQLite DB for testing Unapologetic Poets."""
    test_db_path = Path("./test_swarm_instructions_upoets.db")
    if test_db_path.exists():
        test_db_path.unlink()
    yield test_db_path
    if test_db_path.exists():
        test_db_path.unlink()

@pytest.fixture
def upoets_blueprint_instance():
    with patch('swarm.core.blueprint_base.BlueprintBase._load_and_process_config', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model_instance = MagicMock()
            mock_get_model.return_value = mock_model_instance
            from swarm.blueprints.unapologetic_poets.blueprint_unapologetic_poets import UnapologeticPoetsBlueprint
            # Patch abstract methods to allow instantiation
            UnapologeticPoetsBlueprint.__abstractmethods__ = set()
            instance = UnapologeticPoetsBlueprint(blueprint_id="test_upoets", debug=True)
            instance._config = {'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}
            instance.mcp_server_configs = {}
            return instance

@pytest.mark.skip(reason="SQLite interaction testing needs refinement.")
@patch('blueprints.unapologetic_poets.blueprint_unapologetic_poets.DB_PATH', new_callable=lambda: Path("./test_swarm_instructions_upoets.db"))
@patch('blueprints.unapologetic_poets.blueprint_unapologetic_poets.BlueprintBase._load_configuration', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}})
@patch('blueprints.unapologetic_poets.blueprint_unapologetic_poets.BlueprintBase._get_model_instance')
def test_upoets_db_initialization(mock_get_model, mock_load_config, temporary_db_upoets):
    """Test if the DB table is created and UP sample data loaded."""
    from blueprints.unapologetic_poets.blueprint_unapologetic_poets import UnapologeticPoetsBlueprint

    blueprint = UnapologeticPoetsBlueprint(debug=True)
    blueprint._init_db_and_load_data() # Call directly

    assert temporary_db_upoets.exists()
    with sqlite3.connect(temporary_db_upoets) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_instructions';")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT COUNT(*) FROM agent_instructions WHERE agent_name = ?", ("Gritty Buk",))
        assert cursor.fetchone()[0] > 0

def test_upoets_agent_creation(upoets_blueprint_instance):
    """Test if UnapologeticPoets agent is created correctly."""
    blueprint = upoets_blueprint_instance
    m1 = MagicMock(); m1.name = "memory"
    m2 = MagicMock(); m2.name = "filesystem"
    m3 = MagicMock(); m3.name = "mcp-shell"
    mock_mcp_list = [m1, m2, m3]
    agent = blueprint.create_starting_agent(mcp_servers=mock_mcp_list)
    assert agent is not None
    valid_poets = [
        "Raven Poe", "Mystic Blake", "Bard Whit", "Echo Plath", "Frosted Woods",
        "Harlem Lang", "Verse Neru", "Haiku Bash", "Gritty Buk"
    ]
    assert agent.name in valid_poets

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_upoets_collaboration_flow(temporary_db_upoets):
    """Test a hypothetical multi-agent handoff sequence."""
    # Needs Runner mocking, DB mocking/setup.
    assert False

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_upoets_cli_execution():
    """Test running the blueprint via CLI."""
    # Needs subprocess testing or mocks.
    assert False

import pytest
import asyncio
from src.swarm.blueprints.unapologetic_poets.blueprint_unapologetic_poets import UnapologeticPoetsBlueprint
import re

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.asyncio
async def test_poets_search_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = UnapologeticPoetsBlueprint(blueprint_id="test_poets")
    messages = [{"role": "user", "content": "/search love"}]
    async for _ in blueprint.run(messages, search_mode="code"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "Poets" in out_clean or "Search" in out_clean
    assert "Matches so far:" in out_clean or "Processed" in out_clean
    assert "Found 7 matches" in out_clean

@pytest.mark.asyncio
async def test_poets_analyze_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = UnapologeticPoetsBlueprint(blueprint_id="test_poets")
    messages = [{"role": "user", "content": "/analyze night"}]
    async for _ in blueprint.run(messages, search_mode="semantic"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    assert "Semantic Search" in out_clean or "Poets" in out_clean
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "Analyzed" in out_clean or "Analysis" in out_clean or "semantic" in out_clean.lower()
    assert "Found 7 matches" in out_clean
    assert "Processed" in out_clean

@pytest.mark.asyncio
async def test_upoets_subprocess_launch_and_status():
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = UnapologeticPoetsBlueprint(blueprint_id="test_upoets_subproc")
    # Launch a subprocess (simulate)
    messages = [{"role": "user", "content": "!run sleep 1"}]
    async for chunk in blueprint.run(messages):
        content = chunk["messages"][0]["content"]
        assert "Launched subprocess" in content
        assert "Process ID:" in content
        proc_id = content.split("Process ID:")[1].split("\n")[0].strip()
        break
    # Immediately check status (should be running)
    messages = [{"role": "user", "content": f"!status {proc_id}"}]
    async for chunk in blueprint.run(messages):
        content = chunk["messages"][0]["content"]
        assert "Subprocess status:" in content
        assert "running" in content or "finished" in content
        break
    # Wait for process to finish
    import time
    time.sleep(1.2)
    messages = [{"role": "user", "content": f"!status {proc_id}"}]
    async for chunk in blueprint.run(messages):
        content = chunk["messages"][0]["content"]
        assert "Subprocess status:" in content
        # Parse dict from string
        import ast
        try:
            status_dict = ast.literal_eval(content.split("Subprocess status:")[1].strip())
        except Exception:
            print("DEBUG RAW STATUS:", content)
            status_dict = {}
        # Fallback: check string if dict parse fails
        if not status_dict:
            assert "finished" in content
            assert "exit_code" in content
        else:
            assert status_dict.get("status") == "finished"
            assert "exit_code" in status_dict
        break
