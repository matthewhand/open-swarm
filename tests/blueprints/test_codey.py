import os
import re
import subprocess
import sys
import tempfile


def strip_ansi(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def test_codey_generate_stdout():
    """Test that codey CLI runs in generate mode and outputs to stdout."""
    codey_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey'))
    if not os.path.exists(codey_path):
        raise RuntimeError("codey CLI utility not found. Please enable codey blueprint.")
    result = subprocess.run([sys.executable, codey_path, "Explain what a Python function is."], capture_output=True, text=True)
    out = strip_ansi(result.stdout + result.stderr)
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.returncode == 0
    assert "python function" in out.lower() or "function" in out.lower()

def test_codey_generate_file():
    """Test that codey CLI outputs to a file."""
    codey_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/bin/codey'))
    if not os.path.exists(codey_path):
        raise RuntimeError("codey CLI utility not found. Please enable codey blueprint.")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        output_path = tmp.name
    try:
        result = subprocess.run([sys.executable, codey_path, "What is recursion?", "--output", output_path], capture_output=True, text=True)
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        assert result.returncode == 0
        with open(output_path) as f:
            content = f.read()
        out = strip_ansi(content)
        assert "recursion" in out.lower()
    finally:
        os.remove(output_path)
