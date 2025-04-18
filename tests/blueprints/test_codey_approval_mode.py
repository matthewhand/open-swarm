import subprocess
import sys
import os
import tempfile
import pytest

def test_codey_suggest_skip(tmp_path):
    """Test that codey CLI in suggest mode skips git status when declined."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        pytest.skip("codey CLI utility not found.")
    # Setup temporary git repository
    repo = tmp_path / "repo_skip"
    repo.mkdir()
    # Initialize git and add a file
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    file_path = repo / "foo.txt"
    file_path.write_text("bar\n")
    subprocess.run(["git", "add", "foo.txt"], cwd=str(repo), check=True)
    # Run codey in suggest mode and decline approval
    result = subprocess.run([
        sys.executable,
        codey_path,
        "-a", "suggest",
        "Show me the git status."
    ], cwd=str(repo), input="n\n", capture_output=True, text=True)
    assert result.returncode == 0
    # Should indicate skip
    assert "Skipped git status" in result.stdout

def test_codey_suggest_execute(tmp_path):
    """Test that codey CLI in suggest mode executes git status when approved."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        pytest.skip("codey CLI utility not found.")
    # Setup temporary git repository
    repo = tmp_path / "repo_exec"
    repo.mkdir()
    # Initialize git and add a file
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    file_path = repo / "foo2.txt"
    file_path.write_text("baz\n")
    subprocess.run(["git", "add", "foo2.txt"], cwd=str(repo), check=True)
    # Run codey in suggest mode and approve execution
    result = subprocess.run([
        sys.executable,
        codey_path,
        "-a", "suggest",
        "Show me the git status."
    ], cwd=str(repo), input="y\n", capture_output=True, text=True)
    assert result.returncode == 0
    # Should show git status output containing the file name or changes
    assert "foo2.txt" in result.stdout or "Changes to be committed" in result.stdout