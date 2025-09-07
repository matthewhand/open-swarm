from swarm.blueprints.common.operation_box_utils import display_operation_box


def test_basic_box_output(capsys):
    display_operation_box(
        title="Test Box",
        content="This is a test.",
        style="bold cyan",
        result_count=3,
        params={"param1": "value1"},
        progress_line=2,
        total_lines=5,
        spinner_state="Generating...",
        op_type="search",
        emoji="🔍"
    )
    out, _ = capsys.readouterr()
    assert "Test Box" in out
    assert "This is a test." in out
    assert "Results" in out or "result" in out
    assert "🔍" in out
    assert "Generating..." in out

def test_code_vs_semantic_box(capsys):
    display_operation_box(
        title="Code Search Box",
        content="def foo(): ...",
        style="bold cyan",
        result_count=1,
        params={"query": "foo"},
        progress_line=1,
        total_lines=1,
        spinner_state="Generating.",
        op_type="code_search",
        emoji="💻"
    )
    display_operation_box(
        title="Semantic Search Box",
        content="Found something semantically!",
        style="bold magenta",
        result_count=1,
        params={"query": "semantics"},
        progress_line=1,
        total_lines=1,
        spinner_state="Running...",
        op_type="semantic_search",
        emoji="🧠"
    )
    out, _ = capsys.readouterr()
    assert "Code Search Box" in out
    assert "Semantic Search Box" in out
    assert "💻" in out
    assert "🧠" in out
    assert "Running..." in out

def test_spinner_escalation_box(capsys):
    display_operation_box(
        title="Slow Operation",
        content="Waiting...",
        style="bold yellow",
        result_count=0,
        params={},
        progress_line=0,
        total_lines=10,
        spinner_state="Generating... Taking longer than expected",
        op_type="search",
        emoji="⏳"
    )
    out, _ = capsys.readouterr()
    assert "Taking longer than expected" in out
    assert "⏳" in out
