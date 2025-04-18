import subprocess
import sys
import os
import tempfile

def test_codey_generate_stdout():
    """Test that codey CLI runs in generate mode and outputs to stdout."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        raise RuntimeError("codey CLI utility not found. Please enable codey blueprint.")
    result = subprocess.run([sys.executable, codey_path, "Explain what a Python function is."], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Python function" in result.stdout or "function" in result.stdout

def test_codey_generate_file():
    """Test that codey CLI outputs to a file."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        raise RuntimeError("codey CLI utility not found. Please enable codey blueprint.")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        output_path = tmp.name
    try:
        result = subprocess.run([sys.executable, codey_path, "What is recursion?", "--output", output_path], capture_output=True, text=True)
        assert result.returncode == 0
        with open(output_path) as f:
            content = f.read()
        assert "recursion" in content.lower()
    finally:
        os.remove(output_path)
