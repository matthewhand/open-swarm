"""REQ-159: ADR-005 + README cross-link from the openai-agents section."""

from swarm.core.handoff_graph import repo_root


def test_adr005_has_today_vs_target_and_diagram():
    text = (repo_root() / "docs" / "adr" / "005-kind-bases.md").read_text(encoding="utf-8")
    assert "Intent:" in text and "Success" in text and "Constraints:" in text
    assert "```mermaid" in text
    assert "ApiKindBase" in text
    assert "CliKindBase" in text
    assert "RemoteKindBase" in text
    assert "Today" in text
    assert "Target" in text
    assert "#564" in text or "REQ-156" in text
    assert "10.0.0." not in text
    lowered = text.lower()
    for needle in ("sk-", "github_pat_", "ghp_"):
        assert needle not in lowered


def test_readme_openai_agents_section_links_kind_bases():
    text = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert "docs/adr/005-kind-bases.md" in text
    assert "ApiKindBase" in text
    assert "#570" in text or "REQ-159" in text
