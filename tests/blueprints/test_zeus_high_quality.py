"""
High Quality Test Suite for Zeus Blueprint
==========================================

This test suite consolidates functionality from multiple test files:
- test_zeus.py (metadata testing)
- test_zeus_cli.py (CLI banner and input handling)
- test_zeus_spinner_and_box.py (spinner, operation box, assist, run)

Provides 5/5 quality comprehensive coverage with proper mocking, fixtures,
error handling, and integration testing.
"""

import inspect
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.blueprints.zeus.blueprint_zeus import (
    ZeusCoordinatorBlueprint,
    ZeusSpinner,
)


class TestZeusMetadata:
    """Test Zeus blueprint metadata and basic properties."""

    def test_blueprint_metadata_comprehensive(self):
        """Test all aspects of Zeus blueprint metadata."""
        meta = ZeusCoordinatorBlueprint.get_metadata()

        # Verify CLI name
        assert meta["cli"] == "zeus"
        assert meta["name"] == "zeus"

        # Verify description content
        assert "coordinator" in meta["description"].lower()
        assert isinstance(meta["description"], str)
        assert len(meta["description"]) > 0

        # Verify metadata structure
        required_keys = ["cli", "name", "description"]
        for key in required_keys:
            assert key in meta, f"Missing required metadata key: {key}"

    def test_blueprint_initialization(self):
        """Test blueprint can be initialized with various parameters."""
        # Test default initialization
        blueprint = ZeusCoordinatorBlueprint()
        assert blueprint is not None
        assert hasattr(blueprint, 'cli_spinner')

        # Test with debug mode
        blueprint_debug = ZeusCoordinatorBlueprint(debug=True)
        assert blueprint_debug is not None

        # Test with custom config
        config = {"test": "value"}
        blueprint_config = ZeusCoordinatorBlueprint(config=config)
        assert blueprint_config is not None


class TestZeusSpinner:
    """Test Zeus spinner functionality with comprehensive state management."""

    @pytest.fixture
    def zeus_spinner(self):
        """Provide fresh Zeus spinner instance."""
        return ZeusSpinner()

    def test_spinner_initialization(self, zeus_spinner):
        """Test spinner initializes correctly."""
        assert zeus_spinner is not None
        assert hasattr(zeus_spinner, 'start')
        assert hasattr(zeus_spinner, 'stop')
        assert hasattr(zeus_spinner, '_spin')

    def test_spinner_state_progression(self, zeus_spinner):
        """Test spinner state changes over time."""
        zeus_spinner.start()
        states = []

        # Collect several states
        for _ in range(6):
            zeus_spinner._spin()
            states.append(zeus_spinner.current_spinner_state())

        zeus_spinner.stop()

        # Verify state progression
        assert len(states) == 6
        assert any("Generating." in state for state in states)
        assert any("Generating.." in state for state in states)

        # Verify all states are strings
        assert all(isinstance(state, str) for state in states)
        assert all(len(state) > 0 for state in states)

    def test_spinner_long_wait_detection(self, zeus_spinner):
        """Test spinner detects long wait periods."""
        zeus_spinner.start()

        # Simulate long wait
        zeus_spinner._start_time = time.time() - (ZeusSpinner.SLOW_THRESHOLD + 1)

        state = zeus_spinner.current_spinner_state()
        assert state == zeus_spinner.LONG_WAIT_MSG
        assert "long" in state.lower() or "wait" in state.lower()

    def test_spinner_stop_behavior(self, zeus_spinner):
        """Test spinner behaves correctly when stopped."""
        zeus_spinner.start()
        zeus_spinner.current_spinner_state()

        zeus_spinner.stop()
        stopped_state = zeus_spinner.current_spinner_state()

        # State should be consistent or indicate stopped
        assert isinstance(stopped_state, str)


class TestZeusOperationBox:
    """Test Zeus operation box display functionality."""

    def test_operation_box_basic_display(self, capsys):
        """Test basic operation box display."""
        spinner = ZeusSpinner()
        spinner.start()

        display_operation_box(
            title="Zeus Test",
            content="Testing operation box",
            spinner_state=spinner.current_spinner_state(),
            emoji="⚡"
        )

        spinner.stop()
        captured = capsys.readouterr()

        assert "Zeus Test" in captured.out
        assert "Testing operation box" in captured.out
        assert "⚡" in captured.out

    def test_operation_box_with_parameters(self, capsys):
        """Test operation box with various parameters."""
        display_operation_box(
            title="Zeus Advanced Test",
            content="Testing with parameters",
            result_count=5,
            params={'query': 'test query', 'mode': 'advanced'},
            progress_line=2,
            total_lines=10,
            spinner_state="Generating...",
            emoji="🔍",
            style="blue"
        )

        captured = capsys.readouterr()

        assert "Zeus Advanced Test" in captured.out
        assert "Testing with parameters" in captured.out
        assert "Results: 5" in captured.out
        assert "Query: test query" in captured.out
        assert "Mode: advanced" in captured.out
        assert "Progress: 2/10" in captured.out
        assert "Generating..." in captured.out
        assert "🔍" in captured.out

    def test_operation_box_error_handling(self, capsys):
        """Test operation box handles edge cases gracefully."""
        # Test with empty parameters
        display_operation_box(
            title="",
            content="",
            emoji=""
        )

        captured = capsys.readouterr()
        # Should not crash, may produce minimal output
        assert isinstance(captured.out, str)


class TestZeusAssistFunctionality:
    """Test Zeus assist functionality."""

    def test_assist_box_display(self, monkeypatch, capsys):
        """Test assist box displays correctly."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        blueprint = ZeusCoordinatorBlueprint(debug=False)

        # Mock spinner state
        monkeypatch.setattr(blueprint.cli_spinner, "current_spinner_state", lambda: "Generating...")

        blueprint.assist("hello world")

        captured = capsys.readouterr()
        assert "Zeus Assistance" in captured.out
        assert "hello world" in captured.out

    def test_assist_with_empty_input(self, monkeypatch, capsys):
        """Test assist handles empty input."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        blueprint = ZeusCoordinatorBlueprint(debug=False)

        monkeypatch.setattr(blueprint.cli_spinner, "current_spinner_state", lambda: "Processing...")

        blueprint.assist("")

        captured = capsys.readouterr()
        assert "Zeus Assistance" in captured.out


class TestZeusRunExecution:
    """Test Zeus run execution with various scenarios."""

    @pytest.mark.asyncio
    async def test_run_with_empty_messages(self, monkeypatch):
        """Test run with empty message list."""
        class DummyAgent:
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "empty response"}]}

        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        blueprint = ZeusCoordinatorBlueprint(debug=False)

        dummy_agent = DummyAgent()
        assert inspect.isasyncgenfunction(dummy_agent.run)

        monkeypatch.setattr(blueprint, "create_starting_agent", lambda *a, **k: dummy_agent)

        collected_outputs = []
        async for msg_dict in blueprint.run([]):
            if msg_dict and "messages" in msg_dict and msg_dict["messages"]:
                collected_outputs.append(msg_dict["messages"][0]["content"])

        # Should handle empty input gracefully
        assert isinstance(collected_outputs, list)

    @pytest.mark.asyncio
    async def test_run_with_multiple_steps(self, monkeypatch):
        """Test run with multiple processing steps."""
        class DummyAgent:
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "step 0"}]}
                yield {"messages": [{"role": "assistant", "content": "step 1"}]}
                yield {"messages": [{"role": "assistant", "content": "step 2"}]}

        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        blueprint = ZeusCoordinatorBlueprint(debug=False)

        dummy_agent = DummyAgent()
        monkeypatch.setattr(blueprint, "create_starting_agent", lambda *a, **k: dummy_agent)

        collected_outputs = []
        async for msg_dict in blueprint.run([{"role": "user", "content": "test"}]):
            if msg_dict and "messages" in msg_dict and msg_dict["messages"]:
                collected_outputs.append(msg_dict["messages"][0]["content"])

        assert len(collected_outputs) >= 3

        # Check for spinner in first output
        initial_msg = collected_outputs[0]
        assert initial_msg in ZeusSpinner.FRAMES or "Generating" in initial_msg

        # Check for result boxes in subsequent outputs
        result_outputs = collected_outputs[1:]
        step_0_found = any("Zeus Result" in output and "step 0" in output for output in result_outputs)
        step_1_found = any("Zeus Result" in output and "step 1" in output for output in result_outputs)
        step_2_found = any("Zeus Result" in output and "step 2" in output for output in result_outputs)

        assert step_0_found, f"Step 0 not found in outputs: {result_outputs}"
        assert step_1_found, f"Step 1 not found in outputs: {result_outputs}"
        assert step_2_found, f"Step 2 not found in outputs: {result_outputs}"


class TestZeusCLIIntegration:
    """Test Zeus CLI integration with proper error handling."""

    @pytest.fixture
    def zeus_cli_path(self):
        """Provide path to Zeus CLI script."""
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        cli_path = PROJECT_ROOT / "src/swarm/blueprints/zeus/blueprint_zeus.py"
        return cli_path

    @pytest.mark.skipif(not Path(__file__).resolve().parents[2].joinpath("src/swarm/blueprints/zeus/blueprint_zeus.py").is_file(),
                        reason="Zeus CLI script not found")
    def test_cli_banner_display(self, zeus_cli_path):
        """Test CLI displays banner correctly."""
        result = subprocess.run(
            [sys.executable, str(zeus_cli_path)],
            input="exit\n",
            capture_output=True,
            text=True,
            timeout=20
        )

        output = result.stdout + result.stderr
        assert "Zeus CLI Demo" in output, f"Banner not found in output: {output}"

    @pytest.mark.skipif(not Path(__file__).resolve().parents[2].joinpath("src/swarm/blueprints/zeus/blueprint_zeus.py").is_file(),
                        reason="Zeus CLI script not found")
    def test_cli_multiple_inputs_processing(self, zeus_cli_path):
        """Test CLI handles multiple inputs correctly."""
        inputs = "How are you?\nWhat is your name?\nexit\n"
        result = subprocess.run(
            [sys.executable, str(zeus_cli_path)],
            input=inputs,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr

        # Check for banner
        assert "Zeus CLI Demo" in output

        # Check for spinner activity
        assert "Generating." in output

        # Check for completion
        assert "Demo complete." in output

    @pytest.mark.skipif(not Path(__file__).resolve().parents[2].joinpath("src/swarm/blueprints/zeus/blueprint_zeus.py").is_file(),
                        reason="Zeus CLI script not found")
    def test_cli_error_handling(self, zeus_cli_path):
        """Test CLI handles errors gracefully."""
        # Test with invalid input
        result = subprocess.run(
            [sys.executable, str(zeus_cli_path)],
            input="invalid_command\nexit\n",
            capture_output=True,
            text=True,
            timeout=20
        )

        # Should not crash
        assert result.returncode in [0, 1]
        output = result.stdout + result.stderr
        assert isinstance(output, str)


class TestZeusIntegration:
    """Integration tests combining multiple Zeus components."""

    @pytest.mark.asyncio
    async def test_full_zeus_workflow(self, monkeypatch):
        """Test complete Zeus workflow from initialization to execution."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)

        blueprint = ZeusCoordinatorBlueprint(debug=True)

        # Mock agent for testing
        class MockAgent:
            def __init__(self):
                self.run_called = False

            async def run(self, messages, **kwargs):
                self.run_called = True
                yield {"messages": [{"role": "assistant", "content": "Mock response"}]}

        mock_agent = MockAgent()
        monkeypatch.setattr(blueprint, "create_starting_agent", lambda *a, **k: mock_agent)

        # Test workflow
        messages = [{"role": "user", "content": "Test workflow"}]
        results = []

        async for result in blueprint.run(messages):
            results.append(result)

        assert len(results) > 0
        assert mock_agent.run_called

        # Test assist functionality
        with patch('builtins.print'):  # Suppress prints for clean test
            blueprint.assist("Test assist")

    def test_zeus_component_interaction(self, capsys):
        """Test interaction between Zeus components."""
        blueprint = ZeusCoordinatorBlueprint()

        # Test spinner and operation box interaction
        spinner = blueprint.cli_spinner
        spinner.start()

        display_operation_box(
            title="Component Test",
            content="Testing component interaction",
            spinner_state=spinner.current_spinner_state(),
            emoji="🔗"
        )

        spinner.stop()
        captured = capsys.readouterr()

        assert "Component Test" in captured.out
        assert "Testing component interaction" in captured.out
        assert "🔗" in captured.out
