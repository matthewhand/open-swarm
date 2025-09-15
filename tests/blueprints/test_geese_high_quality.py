"""
High Quality Test Suite for Geese Blueprint
===========================================

This test suite consolidates functionality from multiple test files:
- test_geese.py (basic agent creation and run)
- test_geese_agent_mcp_assignment.py (MCP server assignment)
- test_geese_testmode.py (test mode execution)
- test_geese_spinner_and_box.py (UI components)

Provides comprehensive coverage with proper mocking and test mode handling.
"""

import asyncio
import io
import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from swarm.core.agent_config import AgentConfig
from swarm.core.interaction_types import AgentInteraction


class TestGeeseBlueprintBasic:
    """Test basic blueprint functionality and agent creation."""

    @pytest.fixture
    def mock_console(self):
        """Provide mocked console for testing."""
        return MagicMock(spec=Console)

    @pytest.fixture
    def geese_blueprint(self, mock_console, tmp_path):
        """Provide configured geese blueprint instance."""
        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model_base:
            mock_model_instance = MagicMock(name="MockModelInstanceFromBase")
            async def mock_chat_completion_stream(*args, **kwargs):
                yield {"choices": [{"delta": {"content": "mocked stream part 1"}}]}
                yield {"choices": [{"delta": {"content": " mocked stream part 2"}}]}
            mock_model_instance.chat_completion_stream = mock_chat_completion_stream
            mock_get_model_base.return_value = mock_model_instance

            dummy_config_path = tmp_path / "dummy_geese_config.json"
            dummy_config_content = {
                "llm": {"default": {"provider": "mock", "model": "mock-model"}},
                "settings": {"default_llm_profile": "default"},
                "blueprints": {"test_geese": {}},
                "agents": {
                    "Coordinator": {
                        "instructions": "You are a coordinator.",
                        "model_profile": "default",
                        "tools": []
                    }
                }
            }
            with open(dummy_config_path, "w") as f:
                json.dump(dummy_config_content, f)

            instance = GeeseBlueprint(blueprint_id="test_geese", config_path=str(dummy_config_path))
            instance._config = dummy_config_content
            instance.ux.console = mock_console
            return instance

    def test_blueprint_initialization(self, geese_blueprint):
        """Test blueprint initializes correctly."""
        assert geese_blueprint is not None
        assert geese_blueprint.blueprint_id == "test_geese"

    def test_agent_config_retrieval(self, geese_blueprint):
        """Test retrieving agent configuration."""
        agent_cfg = geese_blueprint._get_agent_config("Coordinator")
        assert agent_cfg is not None
        assert agent_cfg.name == "Coordinator"
        assert "coordinator" in agent_cfg.instructions.lower()

    def test_agent_creation_from_config(self, geese_blueprint):
        """Test creating agent from configuration."""
        agent_cfg = geese_blueprint._get_agent_config("Coordinator")
        agent = geese_blueprint.create_agent_from_config(agent_cfg)
        assert agent is not None
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'instructions')

    def test_agent_run_basic(self, geese_blueprint):
        """Test basic agent run functionality."""
        agent_cfg = geese_blueprint._get_agent_config("Coordinator")
        agent = geese_blueprint.create_agent_from_config(agent_cfg)

        if hasattr(agent, "run"):
            async def collect_chunks():
                chunks = []
                async for chunk in agent.run([{"role": "user", "content": "Quick ping"}]):
                    chunks.append(chunk)
                return chunks

            chunks = asyncio.run(collect_chunks())
            assert len(chunks) > 0
            assert any(isinstance(chunk, AgentInteraction) for chunk in chunks)


class TestGeeseMCPAssignment:
    """Test MCP server assignment functionality."""

    def test_mcp_assignment_in_config(self):
        """Test MCP assignments are properly handled in agent config."""
        cfg = {
            "agents": {
                "Coordinator": {
                    "instructions": "Coordinate the geese.",
                    "model_profile": "default",
                    "tools": []
                }
            },
            "llm": {"default": {"provider": "mock", "model": "mock-model"}},
            "settings": {"default_llm_profile": "default"},
        }

        bp = GeeseBlueprint(
            blueprint_id="test_geese_mcp",
            agent_mcp_assignments={"Coordinator": ["filesystem", "memory"]}
        )
        bp._config = cfg

        agent_cfg = bp._get_agent_config("Coordinator")
        assert isinstance(agent_cfg, AgentConfig)
        assert len(agent_cfg.mcp_servers) == 2
        server_names = [s.name for s in agent_cfg.mcp_servers]
        assert "filesystem" in server_names
        assert "memory" in server_names

    def test_agent_creation_with_mcp_servers(self):
        """Test agent creation handles MCP servers correctly."""
        cfg = AgentConfig(
            name="Coordinator",
            instructions="Coordinate the geese.",
            tools=[],
            model_profile="default",
            mcp_servers=[],
        )
        bp = GeeseBlueprint(blueprint_id="test_geese_create_agent")

        agent = bp.create_agent_from_config(cfg)
        assert agent is not None

        # Check attributes regardless of SDK presence
        assert getattr(agent, "name", None) == "Coordinator"
        assert getattr(agent, "instructions", None) == "Coordinate the geese."
        assert isinstance(getattr(agent, "mcp_servers", []), list)


class TestGeeseTestMode:
    """Test test mode execution and spinner behavior."""

    @pytest.fixture
    def geese_test_mode_instance(self, tmp_path):
        """Provide geese blueprint in test mode."""
        cfg_path = tmp_path / "geese_testmode_config.json"
        cfg = {
            "llm": {"default": {"provider": "mock", "model": "mock-model"}},
            "settings": {"default_llm_profile": "default"},
            "blueprints": {"geese": {}},
        }
        cfg_path.write_text(json.dumps(cfg))

        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model = MagicMock(name="MockModelInstanceForTestMode")
            async def mock_stream(*args, **kwargs):
                if False:
                    yield  # Keep as async generator
            mock_model.chat_completion_stream = mock_stream
            mock_get_model.return_value = mock_model

            bp = GeeseBlueprint(blueprint_id="geese_testmode", config_path=str(cfg_path))
            bp._config = cfg
            return bp

    @pytest.mark.asyncio
    async def test_run_in_test_mode(self, geese_test_mode_instance, monkeypatch):
        """Test blueprint run in test mode with spinner updates."""
        monkeypatch.setenv("SWARM_TEST_MODE", "1")
        bp = geese_test_mode_instance

        chunks = []
        async for ch in bp.run([{"role": "user", "content": "Hello world"}]):
            chunks.append(ch)

        # Should have spinner updates and final interaction
        assert len(chunks) >= 5

        # Check spinner updates
        expected_spinners = ["Generating.", "Generating..", "Generating...", "Running..."]
        for i, label in enumerate(expected_spinners):
            assert isinstance(chunks[i], dict)
            assert chunks[i].get("type") == "spinner_update"
            assert label in chunks[i].get("spinner_state", "")

        # Check final chunk
        final = chunks[-1]
        assert isinstance(final, AgentInteraction)
        assert final.type == "message"
        assert final.final is True
        content = final.content or final.data.get("final_story", "")
        assert "Once upon a time" in content


class TestGeeseUIComponents:
    """Test UI components like operation boxes and spinners."""

    @pytest.fixture
    def geese_ui_instance(self, tmp_path):
        """Provide geese blueprint for UI testing."""
        cfg_path = tmp_path / "geese_ui_config.json"
        cfg = {
            "llm": {"default": {"provider": "mock", "model": "mock-model"}},
            "settings": {"default_llm_profile": "default"},
            "blueprints": {"test_geese": {}},
            "agents": {
                "Coordinator": {
                    "instructions": "You are a coordinator.",
                    "model_profile": "default",
                    "tools": []
                }
            }
        }
        cfg_path.write_text(json.dumps(cfg))

        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance'):
            bp = GeeseBlueprint(blueprint_id="test_geese_ui", config_path=str(cfg_path))
            bp._config = cfg
            return bp

    def test_operation_box_styles(self, geese_ui_instance):
        """Test operation box style rendering."""
        bp = geese_ui_instance
        bp.ux.ux_print_operation_box(title="Test", content="Content")
        bp.ux.console.print.assert_called_once()

    def test_operation_box_error_handling(self, geese_ui_instance):
        """Test operation box handles invalid styles gracefully."""
        bp = geese_ui_instance
        bp.ux.ux_print_operation_box(title="Test", content="Content", style="invalid")
        bp.ux.console.print.assert_called_once()

    def test_operation_box_with_emoji(self, geese_ui_instance):
        """Test operation box with custom emoji."""
        bp = geese_ui_instance
        bp.ux.ux_print_operation_box(title="Success", content="Task completed", emoji="✅")
        bp.ux.console.print.assert_called_once()

    def test_operation_box_comprehensive(self, geese_ui_instance, monkeypatch):
        """Test comprehensive operation box display."""
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buf)

        from swarm.blueprints.common.operation_box_utils import display_operation_box

        display_operation_box(
            title="Geese Operation",
            content="Processing request",
            result_count=3,
            params={'query': 'geese story'},
            progress_line=2,
            total_lines=5,
            spinner_state="Generating...",
            emoji="🦆"
        )

        out = buf.getvalue()
        assert "Processing request" in out
        assert "Progress: 2/5" in out
        assert "Results: 3" in out
        assert "Query: geese story" in out
        assert "Generating..." in out
        assert "🦆" in out


class TestGeeseIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_full_blueprint_workflow(self, tmp_path):
        """Test complete blueprint workflow from init to execution."""
        cfg_path = tmp_path / "geese_integration_config.json"
        cfg = {
            "llm": {"default": {"provider": "mock", "model": "mock-model"}},
            "settings": {"default_llm_profile": "default"},
            "blueprints": {"geese": {}},
            "agents": {
                "Coordinator": {
                    "instructions": "You are a coordinator.",
                    "model_profile": "default",
                    "tools": []
                }
            }
        }
        cfg_path.write_text(json.dumps(cfg))

        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model = MagicMock()
            async def mock_stream(*args, **kwargs):
                yield {"choices": [{"delta": {"content": "Integration test response"}}]}
            mock_model.chat_completion_stream = mock_stream
            mock_get_model.return_value = mock_model

            bp = GeeseBlueprint(blueprint_id="geese_integration", config_path=str(cfg_path))
            bp._config = cfg

            # Test agent creation
            agent_cfg = bp._get_agent_config("Coordinator")
            agent = bp.create_agent_from_config(agent_cfg)
            assert agent is not None

            # Test run execution
            chunks = []
            async for chunk in bp.run([{"role": "user", "content": "Tell me a story"}]):
                chunks.append(chunk)

            assert len(chunks) > 0
            # Should have at least one final message
            assert any(isinstance(chunk, AgentInteraction) and chunk.final for chunk in chunks)
