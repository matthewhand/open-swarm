"""REQ-156: openai-agents graphs live on DEVELOPER.md; README sells the kinds.

#791 parks mermaid off the README. README still names the differentiator
and links the developer doc + the examples pack.
"""

from swarm.core.handoff_graph import repo_root
from helpers.private_net import assert_no_private_ip


def test_developer_doc_has_forced_circular_and_harness_diagrams():
    text = (repo_root() / "docs" / "DEVELOPER.md").read_text(encoding="utf-8")
    assert "## Why openai-agents" in text
    assert "```mermaid" in text
    assert "BA" in text and "Engineer" in text and "Tester" in text
    assert "Skeptic" in text
    assert "API" in text and "CLI" in text and "Remote" in text
    assert "cannot inject" in text.lower() or "stay native" in text.lower()
    assert "openai-agents-handoff-graphs" in text
    assert "#564" in text or "REQ-156" in text
    assert "005-kind-bases.md" in text


def test_readme_attributes_sdk_and_bounds_external_graph_claims():
    text = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/openai/openai-agents-python" in text
    assert "tools and handoffs" in text
    assert "does not inject the SDK" in text
    assert "docs/DEVELOPER.md" in text
    assert "docs/examples/openai-agents-handoff-graphs/README.md" in text
    assert "```mermaid" not in text


def test_readme_names_runtime_kinds_without_claiming_universal_continuity():
    text = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert "`api`, `cli`, `remote` and `team` bases" in text
    assert "ApiKindBase" in text and "blueprints" in text.lower()
    assert "universal cross-harness continuity is not established" in text
    assert "## API and WebUI" in text
    assert "not full OpenAI API parity" in text


def test_readme_keeps_release_lineage_and_publication_limits():
    text = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert "v0.5.4" in text and "19 June 2026" in text
    assert "django_chat resolves its LLM profile" in text
    assert "Unpublished migration alias" in text
    assert "wheel does not bundle the React build" in text
    assert "publisher credentials or" in text
    assert "docs/verification-2026-10-20.md" in text


def test_example_readme_documents_8001_seed_without_secrets():
    pack = repo_root() / "docs" / "examples" / "openai-agents-handoff-graphs" / "README.md"
    text = pack.read_text(encoding="utf-8")
    assert ":8001" in text
    assert "seed_req156_demo.py" in text
    assert "Intent:" in text and "Success:" in text and "Constraints:" in text
    lowered = text.lower()
    for needle in ("sk-", "github_pat_", "ghp_"):
        assert needle not in lowered
    assert_no_private_ip(text)
