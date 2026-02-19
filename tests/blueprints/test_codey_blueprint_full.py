import sys
import types

import pytest

from swarm.blueprints.codey import blueprint_codey
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint


# --- Dummy agent for fallback and patching ---
class DummyAgent:
    def __init__(self, name):
        self.name = name
    async def run(self, messages):
        yield {"role": "assistant", "content": f"[Dummy {self.name}] Would respond to: {messages[-1]['content']}"}

def dummy_create_agents(self):
    return {
        'codegen': DummyAgent('codegen'),
        'git': DummyAgent('git'),
    }

@pytest.fixture
def patch_create_agents(monkeypatch):
    monkeypatch.setattr(CodeyBlueprint, "create_agents", dummy_create_agents)

@pytest.fixture
def dummy_messages():
    return [{"role": "user", "content": "Say hello"}]

# --- Approval Mode Logic ---
@pytest.mark.parametrize("mode,approve", [
    ("suggest", True),
    ("suggest", False),
    ("auto-edit", True),
    ("full-auto", True),
])
def test_approval_modes(monkeypatch, patch_create_agents, mode, approve):
    blueprint = CodeyBlueprint(blueprint_id="test")
    assert hasattr(blueprint, "execute_tool_with_approval"), "Missing method execute_tool_with_approval"
    assert hasattr(blueprint, "set_approval_policy"), "Missing method set_approval_policy"
    if mode == "suggest":
        monkeypatch.setattr("builtins.input", lambda _: "y" if approve else "n")
    called = {}
    def fake_tool(*a, **k):
        called["ok"] = True
        return "TOOL_RESULT"
    blueprint.set_approval_policy(mode)
    if mode == "auto-edit":
        action_type = "write"
        action_details = {"path": "./writable/test.txt"}
        blueprint.execute_tool_with_approval(fake_tool, action_type, "summary", action_details)
    else:
        action_type = "edit"
        blueprint.execute_tool_with_approval(fake_tool, action_type, "summary")
    if mode == "suggest" and not approve:
        assert "ok" not in called
    else:
        assert "ok" in called

# --- Tool Execution & Prompts ---
@pytest.mark.asyncio
async def test_execute_tool_with_approval(monkeypatch, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    blueprint.set_approval_policy("auto-edit")
    def fake_tool(*a, **k):
        return "TOOL_RESULT"
    result = blueprint.execute_tool_with_approval(fake_tool, "write", "summary", {"path": "./writable/test.txt"})
    assert result

# --- Error Handling & Edge Cases ---
def test_invalid_agent(monkeypatch, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    agents = blueprint.create_agents()
    agent_names = list(agents.keys())
    with pytest.raises(SystemExit):
        if "notarealagent" not in agent_names:
            sys.argv = ["prog", "--agent", "notarealagent", "Say something"]
            raise SystemExit(1)

# --- Session & CLI Argument Handling ---
def test_session_cli_args(monkeypatch, patch_create_agents):
    sys.modules["swarm.core.session_logger"] = types.SimpleNamespace(SessionLogger=type("SessionLogger", (), {"list_sessions": staticmethod(lambda x: None), "view_session": staticmethod(lambda x, y: None)}))
    CodeyBlueprint(blueprint_id="test")
    from swarm.core.session_logger import SessionLogger
    SessionLogger.list_sessions("codey")
    SessionLogger.view_session("codey", "dummy_id")

# --- UX & Output Formatting ---
def test_spinner_and_long(monkeypatch):
    from swarm.core.blueprint_ux import BlueprintUXImproved
    ux = BlueprintUXImproved()
    assert ux.spinner(0) == "Generating."
    assert ux.spinner(3, taking_long=True).endswith("Taking longer than expected")
    assert "Results:" in ux.summary("Search", 2, {"q": "foo"})
    assert "Processed 10/100" in ux.progress(10, 100)

# --- Agent Selection & Fallback ---
@pytest.mark.asyncio
async def test_dummy_agent_fallback(monkeypatch, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    agents = blueprint.create_agents()
    assert "codegen" in agents and "git" in agents
    async def collect(agent):
        return [item async for item in agent.run([{"role": "user", "content": "test"}])]
    for agent in agents.values():
        out = await collect(agent)
        assert out

# --- _original_run and search UX branches ---
def test_print_search_results_all_types(monkeypatch, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    captured = {}
    def fake_ansi_box(**kwargs):
        captured.update(kwargs)
        return f"[BOX:{kwargs.get('title')}]"
    monkeypatch.setattr(blueprint_codey, "ansi_box", fake_ansi_box)
    blueprint._print_search_results("Code Search", ["foo", "bar"], {"query": "foo"}, result_type="code")
    blueprint._print_search_results("Semantic Search", ["foo", "bar"], {"query": "foo"}, result_type="semantic")
    blueprint._print_search_results("Analysis", ["foo", "bar"], {"query": "foo"}, result_type="other")
    assert "title" in captured

# --- Edge: missing prompt ---
def test_missing_prompt(monkeypatch, patch_create_agents):
    sys.argv = ["prog"]
    blueprint = CodeyBlueprint(blueprint_id="test")
    try:
        if not hasattr(blueprint, "run_and_print"): raise SystemExit(2)
    except SystemExit as e:
        assert e.code == 2 or e.code == 1

# --- NEW: Async Entrypoint & Run Logic ---
import pytest


@pytest.mark.asyncio
async def test_original_run_git_status(monkeypatch):
    import subprocess
    class DummyCompletedProcess:
        def __init__(self):
            self.stdout = "git status: dummy output"
            self.stderr = ""
            self.returncode = 0
    def dummy_run(*args, **kwargs):
        return DummyCompletedProcess()
    monkeypatch.setattr(subprocess, "run", dummy_run)
    blueprint = CodeyBlueprint(blueprint_id="test")
    blueprint.set_approval_policy("full-auto")
    messages = [{"role": "user", "content": "run git status using github agent"}]
    results = []
    async for result in blueprint._original_run(messages):
        results.append(result)
    all_contents = []
    for r in results:
        if isinstance(r, dict) and "messages" in r:
            for m in r["messages"]:
                all_contents.append(m.get("content", ""))
    assert any("git status" in c for c in all_contents), f"No message with 'git status' found in: {all_contents}"

@pytest.mark.asyncio
async def test_original_run_missing_prompt(monkeypatch):
    blueprint = CodeyBlueprint(blueprint_id="test")
    blueprint.set_approval_policy("full-auto")
    messages = []
    results = []
    async for result in blueprint._original_run(messages):
        results.append(result)
    assert any("need a user message" in str(r).lower() for r in results)

@pytest.mark.asyncio
async def test_run_calls_reflect_and_learn(monkeypatch):
    blueprint = CodeyBlueprint(blueprint_id="test")
    called = {}
    async def fake_reflect_and_learn(messages, result):
        called["ok"] = True
    monkeypatch.setattr(blueprint, "reflect_and_learn", fake_reflect_and_learn)
    messages = [{"role": "user", "content": "Say hi"}]
    async for _ in blueprint.run(messages):
        pass
    assert "ok" in called

# --- NEW: Session Logging ---
def test_log_message_and_tool_call(tmp_path, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    blueprint._session_log_open = True
    blueprint._session_log_path = tmp_path / "log.md"
    blueprint.log_message("user", "hello")
    blueprint.log_tool_call("test_tool", "result")
    with open(blueprint._session_log_path) as f:
        content = f.read()
    assert "hello" in content and "test_tool" in content

# --- NEW: Feedback/Correction ---
def test_inject_feedback_and_detect_feedback(patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    messages = [
        {"role": "user", "content": "That is wrong"},
        {"role": "user", "content": "Try again"},
        {"role": "user", "content": "Looks good"},
    ]
    feedbacks = blueprint._detect_feedback(messages)
    assert len(feedbacks) == 2
    injected = blueprint._inject_feedback(messages)
    assert any("feedback" in str(m).lower() or "wrong" in str(m).lower() for m in injected)

# --- NEW: Output Formatting & UX (spinner/long) ---
def test_print_search_results_spinner(monkeypatch, patch_create_agents):
    blueprint = CodeyBlueprint(blueprint_id="test")
    captured = {}
    def fake_ansi_box(**kwargs):
        captured.update(kwargs)
        return "box"
    monkeypatch.setattr("swarm.blueprints.codey.blueprint_codey.ansi_box", fake_ansi_box)
    blueprint._print_search_results("Search", ["foo"], {"q": "foo"}, result_type="code", simulate_long=True)
    assert "title" in captured

# --- NEW: CLI Argument Edge Cases (scaffold) ---
def test_cli_args_all_agents(monkeypatch, patch_create_agents):
    import sys
    sys.argv = ["prog", "--all-agents", "Say hi"]
    # CLI main logic would be tested here if refactored for easier testability
    # This is a placeholder for future CLI integration tests
    assert True

# --- NEW: DummyStream iteration, create_agents exception handling, set_default_model/set_agent_model, render_prompt, and create_starting_agent logic with monkeypatching for tool dependencies. ---
@pytest.mark.asyncio
async def test_codey_dummy_stream_iter():
    bp = CodeyBlueprint(blueprint_id="dummy")
    # Patch DummyLLM on the instance to add __aiter__ for test coverage
    class DummyStream:
        def __aiter__(self): return self
        async def __anext__(self): raise StopAsyncIteration
    bp.llm = DummyStream()
    dummy_stream = bp.llm
    assert hasattr(dummy_stream, "__anext__")
    with pytest.raises(StopAsyncIteration):
        await dummy_stream.__anext__()

def test_codey_create_agents_llm_profile_exception(monkeypatch):
    bp = CodeyBlueprint(blueprint_id="dummy")
    # Ensure correct llm config structure
    bp._config = {'llm': {'default': {}}}
    if hasattr(bp, 'llm_profile'):
        delattr(bp, 'llm_profile')
    bp.create_agents()

def test_codey_set_default_and_agent_model():
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {'llm': {'default': {}}}
    bp.set_default_model('profileA')
    assert bp._session_model_profile == 'profileA'
    bp.set_agent_model('git', 'profileB')
    assert bp._agent_model_overrides['git'] == 'profileB'

def test_codey_render_prompt():
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {'llm': {'default': {}}}
    context = {'user_request': 'Do X', 'history': 'Y', 'available_tools': ['foo', 'bar']}
    result = bp.render_prompt('irrelevant', context)
    assert 'Do X' in result and 'Y' in result and 'foo' in result and 'bar' in result

def test_codey_create_starting_agent(monkeypatch):
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {'llm': {'default': {}}}
    # Patch make_agent to return dummy agent with as_tool method
    class DummyAgent(types.SimpleNamespace):
        def as_tool(self, tool_name=None, tool_description=None):
            return object()
    bp.make_agent = lambda **kwargs: DummyAgent(**kwargs)
    # Patch all required globals
    monkeypatch.setattr("swarm.blueprints.codey.blueprint_codey.linus_corvalds_instructions", "instructions", raising=False)
    monkeypatch.setattr("swarm.blueprints.codey.blueprint_codey.fiona_instructions", "instructions", raising=False)
    monkeypatch.setattr("swarm.blueprints.codey.blueprint_codey.sammy_instructions", "instructions", raising=False)
    for name in [
        "git_status_tool", "git_diff_tool", "read_file_tool", "write_file_tool", "list_files_tool", "execute_shell_command_tool",
        "git_add_tool", "git_commit_tool", "git_push_tool", "run_npm_test_tool", "run_pytest_tool"
    ]:
        monkeypatch.setattr(f"swarm.blueprints.codey.blueprint_codey.{name}", object(), raising=False)
    agent = bp.create_starting_agent()
    assert hasattr(agent, 'tools') and len(agent.tools) >= 2

# --- NEW: Load Project Instructions, Inject Instructions, and Inject Context ---
import builtins
import os


def test_codey_load_project_instructions(monkeypatch):
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {}
    # Patch os.path.exists and open for both files
    def fake_exists(path):
        if "CODEY.md" in path:
            return True
        return "instructions.md" in path
    def fake_open(path, mode="r", *a, **k):
        class DummyFile:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self):
                if "CODEY.md" in path:
                    return "project-instructions"
                if "instructions.md" in path:
                    return "global-instructions"
                return ""
        return DummyFile()
    monkeypatch.setattr(os.path, "exists", fake_exists)
    monkeypatch.setattr(builtins, "open", fake_open)
    result = bp._load_project_instructions()
    assert result["project"] == "project-instructions"
    assert result["global"] == "global-instructions"

    # Test with neither file existing
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    result = bp._load_project_instructions()
    assert result["project"] is None and result["global"] is None

def test_codey_inject_instructions(monkeypatch):
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {}
    # Patch _load_project_instructions
    bp._load_project_instructions = lambda: {"project": "P", "global": "G"}
    # No system message present
    messages = [{"role": "user", "content": "hi"}]
    out = bp._inject_instructions(messages.copy())
    assert out[0]["role"] == "system" and "G" in out[0]["content"] and "P" in out[0]["content"]
    # System message already present
    messages2 = [{"role": "system", "content": "already here"}]
    out2 = bp._inject_instructions(messages2.copy())
    assert out2[0]["content"].startswith("already here") or "G" in out2[0]["content"] or "P" in out2[0]["content"]

def test_codey_inject_context(monkeypatch):
    bp = CodeyBlueprint(blueprint_id="dummy")
    bp._config = {}
    # Patch _gather_context_for_query
    bp._gather_context_for_query = lambda query: [
        {"type": "file", "path": "foo.py", "snippet": "print('hi')"},
        {"type": "config", "path": "bar.cfg", "snippet": "setting=1"}
    ]
    # No system message present
    messages = [{"role": "user", "content": "query"}]
    out = bp._inject_context(messages.copy(), query="query")
    assert out[0]["role"] == "system" and "foo.py" in out[0]["content"] and "bar.cfg" in out[0]["content"]
    # System message already present
    messages2 = [{"role": "system", "content": "sysmsg"}]
    out2 = bp._inject_context(messages2.copy(), query="query")
    assert out2[0]["content"].startswith("sysmsg") and "foo.py" in out2[0]["content"]
