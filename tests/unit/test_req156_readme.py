"""REQ-156: README sells openai-agents graphs and the three harness types."""

from swarm.core.handoff_graph import repo_root


def test_readme_has_forced_circular_and_harness_diagrams():
    text = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert "## Why openai-agents" in text
    assert "```mermaid" in text
    assert "BA" in text and "Engineer" in text and "Tester" in text
    assert "Skeptic" in text
    assert "API" in text and "CLI" in text and "Remote" in text
    assert "cannot inject" in text.lower() or "stay native" in text.lower()
    assert "docs/examples/openai-agents-handoff-graphs" in text
    assert "#564" in text or "REQ-156" in text


def test_example_readme_documents_8001_seed_without_secrets():
    pack = repo_root() / "docs" / "examples" / "openai-agents-handoff-graphs" / "README.md"
    text = pack.read_text(encoding="utf-8")
    assert ":8001" in text
    assert "seed_req156_demo.py" in text
    assert "Intent:" in text and "Success:" in text and "Constraints:" in text
    lowered = text.lower()
    for needle in ("sk-", "github_pat_", "ghp_"):
        assert needle not in lowered
    assert "10.0.0." not in text
