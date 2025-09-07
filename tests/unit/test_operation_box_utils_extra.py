from swarm.blueprints.common.operation_box_utils import display_operation_box


def test_auto_emoji_and_header_by_op_type(capsys):
    """When no emoji is provided, op_type selects an emoji and header label."""
    display_operation_box(
        title="Search Results",
        content="foo() found",
        op_type="code_search",  # should map to 💻 and [Code Search]
        result_count=1,
        params={"query": "foo"},
    )
    out, _ = capsys.readouterr()
    assert "[Code Search] Search Results" in out
    assert "💻" in out
    assert "Results: 1" in out
    # Params keys are capitalized in output
    assert "Query: foo" in out


def test_spinner_prefix_is_added(capsys):
    """Spinner state should be prefixed with [SPINNER] if not already present."""
    display_operation_box(
        title="Wait",
        content="pending",
        spinner_state="Generating...",
        op_type="search",
    )
    out, _ = capsys.readouterr()
    assert "[SPINNER] Generating..." in out


def test_params_rendering_capitalized_keys(capsys):
    """Params dict keys render capitalized lines in the panel body."""
    display_operation_box(
        title="Param Test",
        content="check",
        params={"alpha": 1, "beta": "two"},
    )
    out, _ = capsys.readouterr()
    assert "Alpha: 1" in out
    assert "Beta: two" in out

