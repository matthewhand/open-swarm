import pytest
from pathlib import Path

# Note: the branch this test came from mocked typer/click/platformdirs via
# sys.modules at import time, which poisoned those packages for the whole
# pytest session (breaking later CLI tests). All three are real deps here.
from swarm.core.swarm_cli import find_entry_point

def test_find_entry_point_single_valid_file(tmp_path):
    """Test find_entry_point with a single valid .py file."""
    (tmp_path / "main.py").write_text("print('hello')")
    assert find_entry_point(tmp_path) == "main.py"

def test_find_entry_point_ignore_underscore_files(tmp_path):
    """Test find_entry_point ignores files starting with '_'."""
    (tmp_path / "_internal.py").write_text("")
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "main.py").write_text("")
    assert find_entry_point(tmp_path) == "main.py"

def test_find_entry_point_ignore_subdirectories(tmp_path):
    """Test find_entry_point ignores subdirectories ending in .py."""
    sub_dir = tmp_path / "subdir.py"
    sub_dir.mkdir()
    assert find_entry_point(tmp_path) is None

    (tmp_path / "main.py").write_text("")
    assert find_entry_point(tmp_path) == "main.py"

def test_find_entry_point_empty_directory(tmp_path):
    """Test find_entry_point with an empty directory."""
    assert find_entry_point(tmp_path) is None

def test_find_entry_point_no_py_files(tmp_path):
    """Test find_entry_point with no .py files."""
    (tmp_path / "README.md").write_text("")
    (tmp_path / "data.json").write_text("{}")
    assert find_entry_point(tmp_path) is None

def test_find_entry_point_multiple_valid_files(tmp_path):
    """Test find_entry_point with multiple valid .py files."""
    # glob order is not guaranteed, but it should return one of them
    files = {"a.py", "b.py", "c.py"}
    for f in files:
        (tmp_path / f).write_text("")

    result = find_entry_point(tmp_path)
    assert result in files
