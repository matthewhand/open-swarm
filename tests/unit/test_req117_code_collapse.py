from pathlib import Path


def test_req117_code_fences_module_exists():
    repo_root = Path(__file__).resolve().parents[2]
    code_fences_ts = repo_root / "webui" / "frontend" / "src" / "lib" / "codeFences.ts"
    assert code_fences_ts.exists()
    content = code_fences_ts.read_text(encoding="utf-8")

    assert "CODE_LINE_THRESHOLD = 10" in content
    assert "os-code--collapsible" in content
    assert "os-code--collapsed" in content
    assert "os-code--expanded" in content
    assert "code-expand" in content
    assert "code-collapse" in content
    assert "code-copy" in content


def test_req117_code_collapse_styles_exist():
    repo_root = Path(__file__).resolve().parents[2]
    index_css = repo_root / "webui" / "frontend" / "src" / "index.css"
    assert index_css.exists()
    content = index_css.read_text(encoding="utf-8")

    assert ".os-code-actions" in content
    assert ".os-code--collapsible.os-code--collapsed" in content
    assert "max-height: 12rem;" in content
