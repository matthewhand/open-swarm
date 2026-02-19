import os
import re
import subprocess
import sys

import pytest


def strip_ansi(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

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
    cmd = [
        sys.executable,
        codey_path,
        "--approval", "suggest",
        "Show me the git status."
    ]
    result = subprocess.run(cmd, cwd=str(repo), input="n\n", capture_output=True, text=True)
    out = strip_ansi(result.stdout + result.stderr)
    found = False
    import ast
    try:
        parsed = ast.literal_eval(out)
        for msg in parsed.get('messages', []):
            content = msg.get('content', '').lower()
            if "skipped git status" in content:
                found = True
                break
    except Exception:
        if "skipped git status" in out.lower():
            found = True
    assert result.returncode == 0
    assert found

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
    cmd = [
        sys.executable,
        codey_path,
        "--approval", "suggest",
        "Show me the git status."
    ]
    result = subprocess.run(cmd, cwd=str(repo), input="y\n", capture_output=True, text=True)
    out = strip_ansi(result.stdout + result.stderr)
    found = False
    import ast
    try:
        parsed = ast.literal_eval(out)
        for msg in parsed.get('messages', []):
            content = msg.get('content', '').lower()
            if "foo2.txt" in content or "changes to be committed" in content:
                found = True
                break
    except Exception:
        if "foo2.txt" in out or "changes to be committed" in out.lower():
            found = True
    assert result.returncode == 0
    assert found
