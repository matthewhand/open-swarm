from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint


def test_inject_context(monkeypatch, tmp_path):
    # Setup fake files for context
    code_file = tmp_path / "foo.py"
    config_file = tmp_path / "settings.yaml"
    doc_file = tmp_path / "README.md"
    code_file.write_text("def foo():\n    pass\n# pytest keyword\n")
    config_file.write_text("setting: true\n# pytest config\n")
    doc_file.write_text("# Project Readme\npytest usage\n")
    # Monkeypatch glob and open to use tmp_path
    import glob
    import os
    orig_open = open
    def fake_glob(pattern, recursive=False):
        if pattern.endswith("*.py"): return [str(code_file)]
        if pattern.endswith("*.yaml"): return [str(config_file)]
        if pattern.endswith("*.md"): return [str(doc_file)]
        return []
    monkeypatch.setattr(glob, "glob", fake_glob)
    monkeypatch.setattr(os.path, "exists", lambda p: str(p) in [str(code_file), str(config_file), str(doc_file)])
    def fake_open(path, mode="r", *a, **kw):
        if str(path) == str(code_file): return orig_open(code_file, mode, *a, **kw)
        if str(path) == str(config_file): return orig_open(config_file, mode, *a, **kw)
        if str(path) == str(doc_file): return orig_open(doc_file, mode, *a, **kw)
        return orig_open(path, mode, *a, **kw)
    monkeypatch.setattr("builtins.open", fake_open)
    blueprint = CodeyBlueprint(blueprint_id="test-context")
    injected = blueprint.test_inject_context()
    sys_msg = injected[0]
    assert sys_msg["role"] == "system"
    assert "Project Context" in sys_msg["content"]
    assert "foo.py" in sys_msg["content"]
    assert "settings.yaml" in sys_msg["content"]
    assert "README.md" in sys_msg["content"]
    assert "pytest" in sys_msg["content"]
