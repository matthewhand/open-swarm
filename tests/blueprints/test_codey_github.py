import subprocess
import sys
import os
import tempfile
import pytest

def test_codey_github_status(monkeypatch):
    """Test that codey CLI can invoke the github agent for git status."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        pytest.skip("codey CLI utility not found. Please enable codey blueprint.")
    # Simulate a repo for git status
    with tempfile.TemporaryDirectory() as repo_dir:
        os.chdir(repo_dir)
        subprocess.run(["git", "init"], check=True)
        # Create a dummy file
        with open("foo.txt", "w") as f:
            f.write("bar\n")
        subprocess.run(["git", "add", "foo.txt"], check=True)
        # Call codey to get git status via github agent
        result = subprocess.run([
            sys.executable, codey_path, "Show me the git status using the github agent."
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert "foo.txt" in result.stdout or "Changes to be committed" in result.stdout
