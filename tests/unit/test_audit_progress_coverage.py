"""
Unit tests for low-coverage modules: audit.py and progress.py
"""
import pytest
from unittest.mock import Mock, patch

from src.swarm.blueprints.common.audit import AuditLogger
from src.swarm.blueprints.common.progress import ProgressRenderer


class TestAuditLogger:
    """Test suite for AuditLogger class."""

    def test_audit_logger_init_disabled(self):
        """Test AuditLogger initialization with disabled logging."""
        logger = AuditLogger(enabled=False)
        assert logger.enabled is False

    def test_audit_logger_init_enabled(self):
        """Test AuditLogger initialization with enabled logging."""
        logger = AuditLogger(enabled=True)
        assert logger.enabled is True

    def test_audit_logger_log_disabled(self):
        """Test that log method does nothing when disabled."""
        logger = AuditLogger(enabled=False)
        with patch('builtins.print') as mock_print:
            logger.log("Test message")
            mock_print.assert_not_called()

    def test_audit_logger_log_enabled(self):
        """Test that log method prints when enabled."""
        logger = AuditLogger(enabled=True)
        with patch('builtins.print') as mock_print:
            logger.log("Test message")
            mock_print.assert_called_once_with("Test message")

    def test_audit_logger_log_with_args(self):
        """Test that log method handles format args correctly."""
        logger = AuditLogger(enabled=True)
        with patch('builtins.print') as mock_print:
            logger.log("Test {} {}", "message", "with")
            mock_print.assert_called_once_with("Test message with")

    def test_audit_logger_log_with_kwargs(self):
        """Test that log method handles kwargs correctly."""
        logger = AuditLogger(enabled=True)
        with patch('builtins.print') as mock_print:
            logger.log("Test message", end='\n', flush=True)
            mock_print.assert_called_once_with("Test message", end='\n', flush=True)


class TestProgressRenderer:
    """Test suite for ProgressRenderer class."""

    def test_progress_renderer_init_defaults(self):
        """Test ProgressRenderer initialization with default values."""
        renderer = ProgressRenderer()
        assert renderer.default_emoji == "✨"
        assert renderer.default_border == "╔"
        assert renderer.default_spinner_states == [
            "Generating.", "Generating..", "Generating...", "Running..."
        ]

    def test_progress_renderer_init_custom(self):
        """Test ProgressRenderer initialization with custom values."""
        custom_states = ["Loading", "Processing", "Done"]
        renderer = ProgressRenderer(
            default_emoji="🚀",
            default_border="═",
            default_spinner_states=custom_states
        )
        assert renderer.default_emoji == "🚀"
        assert renderer.default_border == "═"
        assert renderer.default_spinner_states == custom_states

    def test_render_progress_box_basic(self):
        """Test render_progress_box with basic parameters."""
        renderer = ProgressRenderer()
        
        with patch('src.swarm.blueprints.common.progress.print_search_progress_box') as mock_print:
            renderer.render_progress_box(
                op_type="test_op",
                results=["result1", "result2"],
                summary="Test summary"
            )
            
            mock_print.assert_called_once()
            call_args = mock_print.call_args
            assert call_args[1]['op_type'] == "test_op"
            assert call_args[1]['results'] == ["result1", "result2"]
            assert call_args[1]['summary'] == "Test summary"
            assert call_args[1]['emoji'] == "✨"
            assert call_args[1]['border'] == "╔"

    def test_render_progress_box_custom_params(self):
        """Test render_progress_box with custom parameters."""
        renderer = ProgressRenderer()
        
        with patch('src.swarm.blueprints.common.progress.print_search_progress_box') as mock_print:
            renderer.render_progress_box(
                op_type="custom_op",
                results=["custom_result"],
                summary="Custom summary",
                emoji="🎯",
                border="═",
                spinner_state="Custom state"
            )
            
            mock_print.assert_called_once()
            call_args = mock_print.call_args
            assert call_args[1]['emoji'] == "🎯"
            assert call_args[1]['border'] == "═"
            assert call_args[1]['spinner_state'] == "Custom state"

    def test_render_progress_box_float_spinner(self):
        """Test render_progress_box with float spinner state."""
        renderer = ProgressRenderer()
        
        with patch('src.swarm.blueprints.common.progress.get_spinner_state') as mock_get_state, \
             patch('src.swarm.blueprints.common.progress.print_search_progress_box') as mock_print:
            
            mock_get_state.return_value = "spinner_from_float"
            
            renderer.render_progress_box(
                op_type="test_op",
                results=[],
                summary="Test",
                spinner_state=0.5
            )
            
            mock_get_state.assert_called_once_with(0.5)
            call_args = mock_print.call_args
            assert call_args[1]['spinner_state'] == "spinner_from_float"

    def test_render_progress_box_none_spinner(self):
        """Test render_progress_box with None spinner state."""
        renderer = ProgressRenderer()
        
        with patch('src.swarm.blueprints.common.progress.print_search_progress_box') as mock_print:
            renderer.render_progress_box(
                op_type="test_op",
                results=[],
                summary="Test",
                spinner_state=None
            )
            
            call_args = mock_print.call_args
            assert call_args[1]['spinner_state'] == "Generating."


class TestChucksAngelsBlueprint:
    """Test suite for ChucksAngelsBlueprint class."""

    def test_chucks_angels_blueprint_init(self):
        """Test ChucksAngelsBlueprint initialization."""
        from src.swarm.blueprints.chucks_angels.blueprint_chucks_angels import ChucksAngelsBlueprint
        
        blueprint = ChucksAngelsBlueprint(blueprint_id="test_angels")
        
        assert blueprint.blueprint_id == "test_angels"
        assert blueprint.metadata["name"] == "Chuck's Angels"
        assert blueprint.metadata["version"] == "0.1.1"
        assert "Chuck Norris" in blueprint.metadata["description"]

    async def test_chucks_angels_blueprint_run(self):
        """Test ChucksAngelsBlueprint run method."""
        from src.swarm.blueprints.chucks_angels.blueprint_chucks_angels import ChucksAngelsBlueprint
        
        blueprint = ChucksAngelsBlueprint(blueprint_id="test_angels")
        
        messages = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Response"}
        ]
        
        # Convert async generator to list for testing
        results = []
        async for result in blueprint.run(messages):
            results.append(result)
        
        assert len(results) == 2
        assert results[0]["role"] == "assistant"
        assert "Chuck's Angels" in results[0]["content"]
        assert "Test message" in results[0]["content"]
        assert "Roundhouse kick" in results[1]["content"]

    async def test_chucks_angels_blueprint_no_user_message(self):
        """Test ChucksAngelsBlueprint with no user messages."""
        from src.swarm.blueprints.chucks_angels.blueprint_chucks_angels import ChucksAngelsBlueprint
        
        blueprint = ChucksAngelsBlueprint(blueprint_id="test_angels")
        
        messages = [
            {"role": "assistant", "content": "Response"}
        ]
        
        results = []
        async for result in blueprint.run(messages):
            results.append(result)
        
        assert len(results) == 2
        assert "No user message found" in results[0]["content"]
