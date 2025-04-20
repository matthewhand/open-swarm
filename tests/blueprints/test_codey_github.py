import subprocess
import sys
import os
import tempfile
import pytest
import re
import ast

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

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
        cmd = [sys.executable, codey_path, "Show me the git status using the github agent."]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        out = result.stdout + result.stderr
        found = False
        try:
            parsed = ast.literal_eval(out)
            print("PARSED OUTPUT:", parsed)
            for msg in parsed.get('messages', []):
                content = msg.get('content', '').lower()
                print("MESSAGE CONTENT:", content)
                if "foo.txt" in content or "changes to be committed" in content:
                    found = True
                    break
        except Exception:
            print("RAW OUTPUT:", out)
            if "foo.txt" in out or "changes to be committed" in out.lower():
                found = True
        assert result.returncode == 0
        assert found
