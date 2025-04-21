import subprocess
import sys
import os
import tempfile
import pytest
import asyncio
import re
from src.swarm.blueprints.codey.blueprint_codey import CodeyBlueprint

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def test_codey_generate_meaningful_output():
    """Test that codey CLI returns some non-empty, non-debug output for a known question."""
    codey_path = os.path.expanduser("~/.local/bin/codey")
    if not os.path.exists(codey_path):
        pytest.skip("codey CLI utility not found. Please enable codey blueprint.")
    result = subprocess.run([
        sys.executable, codey_path, "--message", "What is a Python function?", "--no-splash"
    ], capture_output=True, text=True, env={**os.environ, "SWARM_TEST_MODE": "1"})
    assert result.returncode == 0
    output = result.stdout.strip()
    # Accept any output that is not empty and not just spinner/result lines or errors
    assert output and "error" not in output.lower(), f"No meaningful output: {output}"

@pytest.mark.asyncio
async def test_codey_codesearch_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = CodeyBlueprint(blueprint_id="test_codey")
    messages = [{"role": "user", "content": "/codesearch foo"}]
    async for _ in blueprint.run(messages, search_mode="code"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    # Check spinner messages
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    # Check emoji box and search summary
    assert "Code Search" in out_clean
    assert "Matches so far:" in out_clean or "Processed" in out_clean
    assert "Searched filesystem for" in out_clean
    assert "Found 10 matches." in out_clean

@pytest.mark.asyncio
async def test_codey_semanticsearch_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = CodeyBlueprint(blueprint_id="test_codey")
    messages = [{"role": "user", "content": "/semanticsearch bar"}]
    async for _ in blueprint.run(messages, search_mode="semantic"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    assert "Semantic Search" in out_clean
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "Semantic code search for" in out_clean
    assert "Found 10 matches." in out_clean
    assert "Processed" in out_clean
