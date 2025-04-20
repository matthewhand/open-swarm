import sys
import io
import pytest
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint

def test_inject_instructions(monkeypatch, tmp_path):
    # Setup fake CODEY.md and ~/.codey/instructions.md
    codey_md = tmp_path / "CODEY.md"
    global_md = tmp_path / "instructions.md"
    codey_md.write_text("# Project-Level Instructions for Codey\nProject-specific instructions here.")
    global_md.write_text("# Codey Global Instructions\nGlobal guidance here.")
    # Monkeypatch os.path and expanduser to use tmp_path
    import os
    orig_expanduser = os.path.expanduser
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(global_md) if "~/.codey/instructions.md" in p else orig_expanduser(p))
    monkeypatch.setattr(os.path, "exists", lambda p: str(p) == str(codey_md) or str(p) == str(global_md))
    # Patch open to support both paths
    orig_open = open
    def fake_open(path, mode="r", *a, **kw):
        if str(path) == str(codey_md):
            return orig_open(codey_md, mode, *a, **kw)
        if str(path) == str(global_md):
            return orig_open(global_md, mode, *a, **kw)
        return orig_open(path, mode, *a, **kw)
    monkeypatch.setattr("builtins.open", fake_open)
    blueprint = CodeyBlueprint(blueprint_id="test-instructions")
    injected = blueprint.test_inject_instructions()
    sys_msg = injected[0]
    assert sys_msg["role"] == "system"
    # Accept either the standard titles or essential content
    assert (
        "Project-Level Instructions" in sys_msg["content"]
        or "Global Instructions" in sys_msg["content"]
        or "Codey" in sys_msg["content"]
        or "agentic coding assistant" in sys_msg["content"]
    )
    assert any(m["role"] == "user" for m in injected)
