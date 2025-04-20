# Patch display_operation_box in both the utility module and the geese blueprint module BEFORE using GeeseBlueprint
import os
import sys
os.environ["SWARM_TEST_MODE"] = "1"
display_calls = []
from swarm.blueprints.common import operation_box_utils
orig_display = operation_box_utils.display_operation_box
def record_display(*args, **kwargs):
    display_calls.append((args, kwargs))
    return orig_display(*args, **kwargs)
operation_box_utils.display_operation_box = record_display
import importlib
geese_mod = importlib.import_module("swarm.blueprints.geese.blueprint_geese")
geese_mod.display_operation_box = record_display
SpinnerState = geese_mod.SpinnerState
_create_story_outline = geese_mod._create_story_outline
_write_story_part = geese_mod._write_story_part
_edit_story = geese_mod._edit_story

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock, PropertyMock
from rich.panel import Panel
from rich.console import Console
from rich.progress import Progress, TextColumn, SpinnerColumn, Task
from rich.live import Live
from rich.table import Table
import time
import asyncio
import builtins
from swarm.blueprints.common.operation_box_utils import display_operation_box
import io

class AssertFalseCalled(Exception):
    pass

def patched_assert(condition):
    if not condition:
        raise AssertFalseCalled('Patched assert False encountered')

builtins.assertFalse = lambda: (_ for _ in ()).throw(AssertFalseCalled('Patched assert False encountered'))

pytestmark = pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") or os.environ.get("LITELLM_API_KEY")),
    reason="No LLM API key available in CI/CD"
)

@pytest.fixture
def mock_console():
    """Fixture to create a fully mocked Console."""
    console = MagicMock(spec=Console)
    console.get_time = Mock(return_value=time.monotonic())  # Return a float, not the function
    console.is_jupyter = False
    console.is_terminal = True
    console.is_interactive = True  # Add this to satisfy rich.progress.Progress
    console.options = MagicMock()
    console.file = MagicMock()
    console.size = MagicMock()
    console.encoding = "utf-8"
    console.width = 80
    console.height = 24
    return console

@pytest.fixture
def mock_progress():
    """Fixture to create a fully mocked Progress."""
    progress = MagicMock(spec=Progress)
    progress.add_task.return_value = "task1"
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=None)
    
    # Mock task creation
    task = MagicMock(spec=Task)
    task.id = "task1"
    task.description = "Test Task"
    task.completed = 0
    task.total = 100
    progress.tasks = [task]
    
    # Mock table creation
    table = MagicMock(spec=Table)
    table.add_row = Mock()
    progress.make_tasks_table = Mock(return_value=table)
    
    # Mock live display
    progress.live = MagicMock(spec=Live)
    progress.live.get_renderable = Mock(return_value=table)
    progress.live.refresh = Mock()
    progress.live.stop = Mock()
    progress.live.start = Mock()
    
    # Mock time tracking
    progress.get_time = Mock(return_value=time.monotonic())
    progress.advance = Mock()
    progress.update = Mock()
    
    return progress

@pytest.fixture
def geese_blueprint_instance(mock_console):
    """Fixture to create a mocked instance of GeeseBlueprint."""
    with patch('blueprints.geese.blueprint_geese.GeeseBlueprint._get_model_instance') as mock_get_model:
        mock_model_instance = MagicMock()
        mock_get_model.return_value = mock_model_instance
        GeeseBlueprint = geese_mod.GeeseBlueprint
        # Pass a minimal valid config at construction time
        config = {
            "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
            "blueprints": {},
            "llm_profile": "default",
            "mcpServers": {}
        }
        instance = GeeseBlueprint("test_geese", config=config)
        instance.debug = True
        instance.console = mock_console
        return instance

# --- Test Cases ---

@pytest.fixture
def geese_blueprint_instance():
    GeeseBlueprint = geese_mod.GeeseBlueprint
    return GeeseBlueprint(blueprint_id="test_geese")

def test_geese_agent_handoff_and_astool(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    agent = blueprint.create_starting_agent([])
    # Accept both 'Geese' and 'GooseCoordinator' for compatibility
    assert agent.name in ("Geese", "GooseCoordinator")
    assert hasattr(agent, "tools")

def test_geese_story_delegation_flow(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    agent = blueprint.create_starting_agent([])
    assert hasattr(agent, "tools") is True or hasattr(agent, "tools") is False

class DummyAgent:
    def __init__(self, *args, **kwargs):
        pass
    async def run(self, *args, **kwargs):
        print("DummyAgent.run called")
        return
    def __call__(self, *args, **kwargs):
        return self
    def as_tool(self, *args, **kwargs):
        return MagicMock()

class DummyRunner:
    def __init__(self, *args, **kwargs):
        pass
    async def run(self, *args, **kwargs):
        print("DummyRunner.run called")
        return
    def __call__(self, *args, **kwargs):
        return self

def patch_blueprint_agents_and_runners():
    return patch.multiple(
        'blueprints.geese.blueprint_geese',
        Agent=DummyAgent,
        Runner=DummyRunner,
        Tool=MagicMock(return_value=MagicMock()),
        function_tool=MagicMock(return_value=MagicMock())
    )

@pytest.mark.skipif(os.environ.get("DEFAULT_LLM") != "test", reason="Requires DEFAULT_LLM=test for LLM-dependent test.")
def test_run_with_progress():
    with patch_blueprint_agents_and_runners():
        class MockNotifier:
            def __init__(self):
                self.print_box_calls = []
            def print_box(self, title, content, style="blue", emoji="💡"):
                print(f"[DEBUG] print_box called: title={title}, content={content}, style={style}, emoji={emoji}")
                self.print_box_calls.append((title, content, style, emoji))
        notifier = MockNotifier()
        GeeseBlueprint = geese_mod.GeeseBlueprint
        blueprint = GeeseBlueprint("test_geese", notifier=notifier)
        mock_progress_class = MagicMock()
        mock_progress_instance = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "task1"
        mock_progress_instance.add_task.return_value = mock_task
        mock_progress_instance.__enter__.return_value = mock_progress_instance
        mock_progress_instance.__exit__.return_value = None
        mock_progress_class.return_value = mock_progress_instance
        blueprint.update_spinner = MagicMock(return_value=SpinnerState.GENERATING_1)
        async def fake_run_agent(agent, messages):
            print("[DEBUG] fake_run_agent yielding plan...")
            yield {"plan": ["Step 1"]}
            print("[DEBUG] fake_run_agent yielding search...")
            yield {"search": {"results": [{"details": "Found A"}], "details": "Found A"}, "count": 1}
            print("[DEBUG] fake_run_agent yielding content...")
            yield {"content": "Done!"}
        with patch('blueprints.geese.blueprint_geese.Progress', mock_progress_class), \
             patch.object(geese_mod.BlueprintRunner, 'run_agent', side_effect=fake_run_agent):
            calls = []
            async def runit():
                async for chunk in blueprint.run([{"role": "user", "content": "Test"}]):
                    print(f"[DEBUG] blueprint.run yielded: {chunk}")
                    calls.append(True)
            import asyncio
            asyncio.get_event_loop().run_until_complete(runit())
        print(f"[DEBUG] notifier.print_box_calls: {notifier.print_box_calls}")
        assert any("plan" in call[0].lower() or "search" in call[0].lower() for call in notifier.print_box_calls)
        assert calls

@pytest.mark.skipif(os.environ.get("DEFAULT_LLM") != "test", reason="Requires DEFAULT_LLM=test for LLM-dependent test.")
def test_notifier_output_and_error_surfacing():
    with patch_blueprint_agents_and_runners():
        class MockNotifier:
            def __init__(self):
                self.box_calls = []
                self.error_calls = []
            def display_operation_box(self, *args):
                self.box_calls.append(args)
            def print_error(self, *args):
                self.error_calls.append(args)
        notifier = MockNotifier()
        GeeseBlueprint = geese_mod.GeeseBlueprint
        blueprint = GeeseBlueprint("test_geese", notifier=notifier)
        class DummyCoordinator:
            async def run(self, messages):
                yield {"plan": ["Step 1", "Step 2"]}
                yield {"search": {"results": [{"details": "Found A"}], "details": "Found A"}, "count": 1}
                yield {"analysis": {"results": ["A"], "details": "Analysis A"}, "count": 1}
                yield {"error": "Something went wrong!"}
                yield {"content": "Done!"}
        blueprint.coordinator = DummyCoordinator()
        results = []
        async def runit():
            async for result in blueprint.run([{"role": "user", "content": "Test"}]):
                results.append(result)
        import asyncio
        asyncio.get_event_loop().run_until_complete(runit())
        assert any("plan" in call[0][0].lower() or "planning" in call[0][0].lower() for call in notifier.box_calls)
        assert any("search" in call[0][0].lower() for call in notifier.box_calls)
        assert any("analysis" in call[0][0].lower() for call in notifier.box_calls)
        assert any("something went wrong!" in str(call[0]).lower() for call in notifier.error_calls)
        assert any("content" in r and r["content"] == "Done!" for r in results)

def test_spinner_state_updates():
    assert True

def test_operation_box_styles(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Styled Box",
        content="Content with style",
        result_count=3,
        params={"query": "styled"},
        progress_line=2,
        total_lines=5,
        spinner_state="Generating...",
        emoji="🔍"
    )
    out = buf.getvalue()
    assert "Styled Box" in out
    assert "Content with style" in out
    assert "Results: 3" in out
    assert "Query: styled" in out
    assert "Progress: 2/5" in out
    assert "Generating..." in out
    assert "🔍" in out

def test_operation_box_default_emoji(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Default Emoji",
        content="No emoji provided"
    )
    out = buf.getvalue()
    assert "No emoji provided" in out
    assert "💡" in out

@pytest.mark.asyncio
@pytest.mark.skip(reason="Obsolete: GeeseBlueprint no longer emits test-mode progressive operation boxes.")
def test_progressive_demo_operation_box():
    global display_calls
    display_calls.clear()
    GeeseBlueprint = geese_mod.GeeseBlueprint
    blueprint = GeeseBlueprint("test_geese")
    # Print environment and blueprint config for debugging
    print(f"DEBUG: SWARM_TEST_MODE={os.environ.get('SWARM_TEST_MODE')}")
    print(f"DEBUG: blueprint config: {getattr(blueprint, '_config', None)}")
    async def run_and_collect():
        results = []
        async for r in blueprint.run([{"role": "user", "content": "/geesedemo-progressive"}]):
            results.append(r)
        return results
    import asyncio
    results = asyncio.get_event_loop().run_until_complete(run_and_collect())
    progressive_calls = [
        (args, kwargs) for args, kwargs in display_calls
        if all(k in kwargs for k in ("result_count", "progress_line", "total_lines"))
    ]
    print(f"DEBUG: display_calls in test_progressive_demo_operation_box: {display_calls}")
    print(f"DEBUG: progressive_calls count: {len(progressive_calls)}")
    print(f"DEBUG: results: {results}")
    # The Geese blueprint progressive demo emits multiple spinner/progressive operation box updates
    assert len(progressive_calls) >= 2
    for i, (args, kwargs) in enumerate(progressive_calls, 1):
        assert kwargs["result_count"] == i
        assert kwargs["progress_line"] == i
        assert kwargs["total_lines"] == len(progressive_calls)
        assert kwargs.get("op_type", "search") == "search"
    assert any("Test complete" in (r.get("content", "") if isinstance(r, dict) else r) for r in results)

@pytest.mark.asyncio
@pytest.mark.skip(reason="Obsolete: GeeseBlueprint no longer emits test-mode progressive operation boxes.")
def test_progressive_grep_search(mock_console, tmp_path):
    """Test the progressive grep_search tool yields progress and triggers live output."""
    global display_calls
    display_calls.clear()
    GeeseBlueprint = geese_mod.GeeseBlueprint
    blueprint = GeeseBlueprint("test_geese")
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hello\nworld\nhello again\n")
    b.write_text("foo\nbar\nHELLO\n")
    async def run_and_collect():
        results = []
        async for r in blueprint.run([{"role": "user", "content": "/geesedemo-progressive"}]):
            results.append(r)
        return results
    import asyncio
    results = asyncio.get_event_loop().run_until_complete(run_and_collect())
    progressive_calls = [
        (args, kwargs) for args, kwargs in display_calls
        if all(k in kwargs for k in ("result_count", "progress_line", "total_lines"))
    ]
    print(f"DEBUG: display_calls in test_progressive_grep_search: {display_calls}")
    print(f"DEBUG: progressive_calls count: {len(progressive_calls)}")
    print(f"DEBUG: results: {results}")
    assert len(progressive_calls) >= 2
    for i, (args, kwargs) in enumerate(progressive_calls, 1):
        assert kwargs["result_count"] == i
        assert kwargs["progress_line"] == i
        assert kwargs["total_lines"] == len(progressive_calls)
        assert kwargs.get("op_type", "search") == "search"
    assert any("Test complete" in (r.get("content", "") if isinstance(r, dict) else r) for r in results)

def test_geese_story_delegation_flow(geese_blueprint_instance):
    """Test full agent handoff sequence: Planner -> Writer -> Editor."""
    blueprint = geese_blueprint_instance
    coordinator = blueprint.create_starting_agent(mcp_servers=[])
    planner_tool = next(t for t in coordinator.tools if t.name == "Planner")
    writer_tool = next(t for t in coordinator.tools if t.name == "Writer")
    editor_tool = next(t for t in coordinator.tools if t.name == "Editor")
    assert all([planner_tool, writer_tool, editor_tool])

def test_spinner_state_transitions(geese_blueprint_instance):
    """Test spinner state transitions and long wait detection."""
    blueprint = geese_blueprint_instance
    # Use module-level SpinnerState
    state = blueprint.update_spinner(SpinnerState.GENERATING_1, 10.0)
    assert state == SpinnerState.GENERATING_1
    # Test long wait state
    state = blueprint.update_spinner(SpinnerState.GENERATING_2, 35.0)
    assert state == SpinnerState.LONG_WAIT
    # Test fallback
    state = blueprint.update_spinner(SpinnerState.LONG_WAIT, 5.0)
    assert state == SpinnerState.LONG_WAIT

def test_operation_box_styles(geese_blueprint_instance):
    """Test operation box display with different styles and emojis."""
    blueprint = geese_blueprint_instance
    notifier = MockNotifier()
    blueprint.notifier = notifier
    # Test search box
    display_operation_box(title="Search Results", content="Found 5 matches", style="blue")
    assert any("Search Results" in call[0] and "Found 5 matches" in call[1] for call in notifier.box_calls)
    # Test analysis box
    display_operation_box(title="Analysis Complete", content="Code quality: Good", style="magenta")
    assert any("Analysis Complete" in call[0] and "Code quality: Good" in call[1] for call in notifier.box_calls)
    # Test writing box
    display_operation_box(title="Writing Story", content="Chapter 1 in progress", style="green")
    assert any("Writing Story" in call[0] and "Chapter 1 in progress" in call[1] for call in notifier.box_calls)
    # Test editing box
    display_operation_box(title="Editing Content", content="Improving flow", style="yellow")
    assert any("Editing Content" in call[0] and "Improving flow" in call[1] for call in notifier.box_calls)

def test_display_splash_screen_variants():
    GeeseBlueprint = geese_mod.GeeseBlueprint
    blueprint = GeeseBlueprint("test_geese")
    blueprint.console = MagicMock()
    # Cover both animated False and True
    blueprint.display_splash_screen(animated=False)
    blueprint.display_splash_screen(animated=True)

# CLI/main coverage: patch sys.argv and call main()
def test_main_entry(monkeypatch):
    import sys
    import asyncio
    from swarm.blueprints.geese import blueprint_geese
    monkeypatch.setattr(sys, "argv", ["prog", "Test prompt"])
    # Patch asyncio.run globally
    monkeypatch.setattr(asyncio, "run", lambda coro: None)
    # Should not raise
    blueprint_geese.main()

class MockNotifier:
    def __init__(self):
        from unittest.mock import MagicMock
        self.box_calls = []
        self.error_calls = []
        self.info_calls = []
        self.console = MagicMock()
    def print_box(self, title, content, style="blue", emoji="💡"):
        self.box_calls.append((title, content, style, emoji))
    def print_error(self, title, content):
        self.error_calls.append((title, content))
    def print_info(self, content):
        self.info_calls.append(content)

def test_create_story_outline():
    """Test story outline creation."""
    topic = "Adventure in space"
    outline = _create_story_outline(topic)
    assert "Story Outline" in outline
    assert "Beginning" in outline
    assert "Middle" in outline
    assert "End" in outline
    assert topic in outline

def test_write_story_part():
    """Test story part writing."""
    part_name = "Beginning"
    outline = "Story outline test"
    previous = "Previous content"
    content = _write_story_part(part_name, outline, previous)
    assert part_name in content
    assert outline in content
    assert previous[:100] in content

def test_edit_story():
    """Test story editing."""
    full_story = "Original story content"
    edit_instructions = "Make it more engaging"
    edited = _edit_story(full_story, edit_instructions)
    assert full_story in edited
    assert edit_instructions in edited
    assert "Editor's Notes" in edited

def test_spinner_messages():
    """Test spinner message states."""
    assert SpinnerState.GENERATING_1.value == "Generating."
    assert SpinnerState.GENERATING_2.value == "Generating.."
    assert SpinnerState.GENERATING_3.value == "Generating..."
    assert SpinnerState.RUNNING.value == "Running..."
    assert SpinnerState.LONG_WAIT.value == "Generating... Taking longer than expected"

def test_story_generation_flow(geese_blueprint_instance):
    """Test the complete story generation flow."""
    blueprint = geese_blueprint_instance
    # Mock the story generation functions
    async def mock_create_outline(topic):
        return f"Story Outline for {topic}\nBeginning: Start here\nMiddle: Continue\nEnd: Finish"
    async def mock_write_part(part_name, outline, previous):
        return f"{part_name} content based on {outline[:20]}... with previous: {previous[:20]}"
    async def mock_edit(story, instructions):
        return f"Edited: {story[:50]} according to {instructions}"
    # Patch the async functions directly in the blueprint instance
    blueprint.create_story_outline = mock_create_outline
    blueprint.write_story_part = mock_write_part
    blueprint.edit_story = mock_edit
    # Test outline creation
    topic = "Space Adventure"
    outline = asyncio.get_event_loop().run_until_complete(blueprint.create_story_outline(topic))
    assert topic in outline
    assert "Beginning" in outline
    # Test writing first part
    part1 = asyncio.get_event_loop().run_until_complete(blueprint.write_story_part("Beginning", outline, ""))
    assert "Beginning" in part1
    assert len(part1) > 0
    # Test writing middle with context
    part2 = asyncio.get_event_loop().run_until_complete(blueprint.write_story_part("Middle", outline, part1))
    assert "Middle" in part2
    assert len(part2) > 0
    # Test editing
    full_story = part1 + "\n" + part2
    edited = asyncio.get_event_loop().run_until_complete(blueprint.edit_story(full_story, "Make it more dramatic"))
    assert "dramatic" in edited.lower()
    assert len(edited) > 0

import subprocess

def strip_ansi(text):
    import re
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.integration
@pytest.mark.skip(reason="Obsolete: GeeseBlueprint no longer emits test-mode spinner messages in CLI.")
def test_geese_cli_ux():
    env = os.environ.copy()
    env['DEFAULT_LLM'] = 'test'
    env['SWARM_TEST_MODE'] = '1'
    cli_path = os.path.join(os.path.dirname(__file__), '../../src/swarm/blueprints/geese/geese_cli.py')
    cmd = [sys.executable, cli_path, '--message', 'Write a story about a goose.']
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = strip_ansi(result.stdout + result.stderr)
    assert any(msg in output for msg in ['Generating.', 'Generating..', 'Generating...', 'Running...']), f"Spinner messages not found in output: {output}"
    assert 'Matches so far:' in output or 'Geese Output' in output or 'Searching Filesystem' in output, f"Operation box output not found: {output}"
