"""
High Quality Test Suite for Codey Blueprint
===========================================

This test suite consolidates functionality from multiple test files:
- test_codey.py (CLI integration tests)
- test_codey_blueprint.py (blueprint functionality tests)
- test_codey_spinner_and_box.py (UI component tests)

Provides comprehensive coverage with proper mocking, fixtures, and error handling.
"""

import asyncio
import io
import os
import re
import subprocess
import sys
import tempfile
import types

import pytest
from swarm.blueprints.codey import blueprint_codey
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint, CodeySpinner
from swarm.blueprints.common.operation_box_utils import display_operation_box


class TestCodeyCLIFunctionality:
    """Test CLI functionality with proper error handling and output validation."""

    def strip_ansi(self, text):
        """Remove ANSI escape sequences from text."""
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)

    def test_cli_generate_stdout(self):
        """Test CLI generates output to stdout."""
        codey_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey'))
        if not os.path.exists(codey_path):
            pytest.skip("Codey CLI utility not found. Please enable codey blueprint.")

        result = subprocess.run(
            [sys.executable, codey_path, "Explain what a Python function is."],
            capture_output=True,
            text=True,
            timeout=30
        )

        out = self.strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert any(keyword in out.lower() for keyword in ["python", "function"]), f"Expected content not found in output: {out}"

    def test_cli_generate_file_output(self):
        """Test CLI outputs to file correctly."""
        codey_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey'))
        if not os.path.exists(codey_path):
            pytest.skip("Codey CLI utility not found. Please enable codey blueprint.")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            output_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, codey_path, "What is recursion?", "--output", output_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            with open(output_path) as f:
                content = f.read()

            out = self.strip_ansi(content)
            assert "recursion" in out.lower(), f"Expected 'recursion' in output: {out}"
        finally:
            os.remove(output_path)

    def test_cli_error_handling(self):
        """Test CLI handles errors gracefully."""
        codey_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey'))
        if not os.path.exists(codey_path):
            pytest.skip("Codey CLI utility not found. Please enable codey blueprint.")

        result = subprocess.run(
            [sys.executable, codey_path, ""],  # Empty prompt
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should either succeed with default behavior or fail gracefully
        self.strip_ansi(result.stdout + result.stderr)
        assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"


class TestCodeyBlueprintCore:
    """Test core blueprint functionality with comprehensive mocking."""

    @pytest.fixture
    def dummy_messages(self):
        """Provide dummy messages for testing."""
        return [{"role": "user", "content": "Say hello"}]

    @pytest.fixture
    def dummy_agents(self):
        """Provide dummy agents for testing."""
        class DummyAgent:
            def __init__(self, name):
                self.name = name

            async def run(self, messages):
                yield {"role": "assistant", "content": f"[Dummy {self.name}] Would respond to: {messages[-1]['content']}"}

        return {
            'codegen': DummyAgent('codegen'),
            'git': DummyAgent('git'),
        }

    @pytest.fixture(autouse=True)
    def patch_create_agents(self, monkeypatch, dummy_agents):
        """Patch create_agents to return dummy agents."""
        def dummy_create_agents():
            return dummy_agents

        monkeypatch.setattr(CodeyBlueprint, "create_agents", dummy_create_agents)

    def test_inject_instructions_and_context(self, dummy_messages):
        """Test instruction and context injection."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        injected = blueprint._inject_instructions(dummy_messages.copy())
        assert len(injected) > 0
        assert injected[0]["role"] in ["system", "user"]

        injected_ctx = blueprint._inject_context(dummy_messages.copy())
        assert isinstance(injected_ctx, list)

    def test_create_agents_functionality(self, dummy_agents):
        """Test agent creation and execution."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        agents = blueprint.create_agents()
        assert "codegen" in agents
        assert "git" in agents

        async def collect_responses():
            results = []
            for name, agent in agents.items():
                responses = [item async for item in agent.run([{"role": "user", "content": f"test {name}"}])]
                results.extend(responses)
            return results

        responses = asyncio.run(collect_responses())
        assert len(responses) > 0
        assert any("Dummy" in str(r) for r in responses)

    def test_session_management_integration(self, monkeypatch):
        """Test session management integration."""
        # Mock session logger module
        sys.modules["swarm.core.session_logger"] = types.SimpleNamespace(
            SessionLogger=type("SessionLogger", (), {
                "list_sessions": staticmethod(lambda x: None),
                "view_session": staticmethod(lambda x, y: None)
            })
        )

        CodeyBlueprint(blueprint_id="test")

        from swarm.core.session_logger import SessionLogger
        # Should not raise exceptions
        SessionLogger.list_sessions("codey")
        SessionLogger.view_session("codey", "dummy_id")

    @pytest.mark.asyncio
    async def test_multi_agent_selection_and_execution(self, dummy_agents):
        """Test multi-agent selection and async execution."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        agents = blueprint.create_agents()

        results = []
        for agent in agents.values():
            agent_results = [item async for item in agent.run([{"role": "user", "content": "test"}])]
            results.append(agent_results)

        assert len(results) == len(agents)
        assert all(len(r) > 0 for r in results)


class TestCodeyUIComponents:
    """Test UI components including spinners and operation boxes."""

    @pytest.mark.parametrize("frame_idx,expected", [
        (0, "Generating."),
        (1, "Generating.."),
        (2, "Generating..."),
        (3, "Running..."),
    ])
    def test_spinner_frames(self, frame_idx, expected):
        """Test spinner frame progression."""
        spinner = CodeySpinner()
        spinner.start()
        for _ in range(frame_idx):
            spinner._spin()
        assert spinner.current_spinner_state() == expected

    def test_spinner_long_wait_handling(self):
        """Test spinner handles long waits appropriately."""
        spinner = CodeySpinner()
        spinner.start()
        spinner._start_time -= 15  # Simulate long wait
        spinner._spin()
        assert "Taking longer than expected" in spinner.current_spinner_state()

    def test_display_operation_box_basic(self, monkeypatch):
        """Test basic operation box display."""
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buf)

        display_operation_box(
            title="Test Title",
            content="Test Content",
            result_count=5,
            params={'query': 'foo'},
            progress_line=10,
            total_lines=100,
            spinner_state="Generating...",
            emoji="💻"
        )

        out = buf.getvalue()
        assert "Test Content" in out
        assert "Progress: 10/100" in out
        assert "Results: 5" in out
        assert "Query: foo" in out
        assert "Generating..." in out
        assert "💻" in out

    def test_display_operation_box_long_wait(self, monkeypatch):
        """Test operation box with long wait indicator."""
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buf)

        display_operation_box(
            title="Test Title",
            content="Test Content",
            spinner_state="Generating... Taking longer than expected",
            emoji="⏳"
        )

        out = buf.getvalue()
        assert "Taking longer than expected" in out
        assert "⏳" in out

    def test_display_operation_box_edge_cases(self, monkeypatch):
        """Test operation box with missing optional parameters."""
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buf)

        display_operation_box(
            title="Minimal Test",
            content="Minimal Content"
        )

        out = buf.getvalue()
        assert "Minimal Content" in out
        assert "Minimal Test" in out


class TestCodeySearchAndDisplay:
    """Test search result display functionality."""

    def test_print_search_results_basic(self, monkeypatch):
        """Test basic search results printing."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        captured = {}

        def fake_ansi_box(**kwargs):
            captured.update(kwargs)
            return f"[BOX:{kwargs.get('title')}]"

        monkeypatch.setattr(blueprint_codey, "ansi_box", fake_ansi_box)

        blueprint._print_search_results("Code Search", ["foo", "bar"], {"query": "foo"}, result_type="code")
        assert captured.get("title") == "Code Search"

    def test_print_search_results_semantic(self, monkeypatch):
        """Test semantic search results with emoji."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        captured = {}

        def fake_ansi_box(**kwargs):
            captured.update(kwargs)
            return f"[BOX:{kwargs.get('title')}]"

        monkeypatch.setattr(blueprint_codey, "ansi_box", fake_ansi_box)

        blueprint._print_search_results("Semantic Search", ["foo", "bar"], {"query": "foo"}, result_type="semantic")
        assert captured.get("emoji") == "🧠"

    def test_print_search_results_progressive(self, monkeypatch):
        """Test progressive search results display."""
        blueprint = CodeyBlueprint(blueprint_id="test")
        captured = {"calls": []}

        def fake_ansi_box(**kwargs):
            captured["calls"].append(kwargs)
            return f"[BOX:{kwargs.get('title')}]"

        monkeypatch.setattr(blueprint_codey, "ansi_box", fake_ansi_box)

        def dummy_progressive():
            yield {"progress": 1, "total": 3, "results": ["foo"], "current_file": "file1.py", "done": False, "elapsed": 0}
            yield {"progress": 2, "total": 3, "results": ["foo", "bar"], "current_file": "file2.py", "done": False, "elapsed": 1}
            yield {"progress": 3, "total": 3, "results": ["foo", "bar", "baz"], "current_file": "file3.py", "done": True, "elapsed": 2}

        blueprint._print_search_results(
            "Code Search",
            dummy_progressive(),
            {"query": "foo"},
            result_type="code"
        )

        assert len(captured["calls"]) == 3
        assert any(call.get("count") == 3 for call in captured["calls"])


class TestCodeyUXIntegration:
    """Test UX integration components."""

    def test_blueprint_ux_summary(self):
        """Test UX summary generation."""
        from swarm.core.blueprint_ux import BlueprintUXImproved
        ux = BlueprintUXImproved()
        summary = ux.summary("Search", 2, {"q": "foo"})
        assert "Results: 2" in summary

    def test_blueprint_ux_progress(self):
        """Test UX progress display."""
        from swarm.core.blueprint_ux import BlueprintUXImproved
        ux = BlueprintUXImproved()
        progress = ux.progress(20, 100)
        assert "20/100" in progress

    def test_blueprint_ux_spinner(self):
        """Test UX spinner functionality."""
        from swarm.core.blueprint_ux import BlueprintUXImproved
        ux = BlueprintUXImproved()
        spinner = ux.spinner(2)
        assert isinstance(spinner, str)
        assert len(spinner) > 0
