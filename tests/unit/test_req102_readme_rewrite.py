"""#791: README is the user front door; internals live in docs/DEVELOPER.md.

Parent #466 closed by #785. This file locks the remaining shape bump:
WebUI-first + kinds lock stay (landed #785); mermaid / layout / CI live
on DEVELOPER.md; README must not become a developer novel again.
"""

from swarm.core.handoff_graph import repo_root
from helpers.private_net import assert_no_private_ip


def _readme() -> str:
    return (repo_root() / "README.md").read_text(encoding="utf-8")


def _developer() -> str:
    return (repo_root() / "docs" / "DEVELOPER.md").read_text(encoding="utf-8")


def test_readme_explains_shared_surfaces_and_real_kind_bases():
    text = _readme()
    assert "## Install current source" in text
    assert "## API and WebUI" in text
    assert "ApiKindBase" in text and "Django" in text
    assert "CLI adapters" in text and "remote adapters" in text
    assert "Team rosters" in text
    assert "does not inject" in text
    for name in ("Hermes", "OpenMousBot", "Rakazo", "Herdr"):
        assert name in text
    assert "docs/DEVELOPER.md" in text


def test_readme_separates_unreleased_alpha_from_published_cut():
    text = _readme()
    assert "open-swarm==0.5.4" in text
    assert "os-core 0.6.0a1" in text
    assert "Unreleased alpha" in text
    assert "Not available when checked" in text
    assert "Merging a PR does not publish to PyPI" in text
    assert "Experimental alpha" in text


def test_readme_has_a_brief_architecture_and_practical_front_door():
    text = _readme()
    architecture = text.split("## Architecture", 1)[1].split("## Install", 1)[0]
    assert 20 < len(architecture.split()) < 220
    assert "```mermaid" not in text
    assert "## Bundled Blueprints" not in text
    assert "## Environment Variables" not in text
    assert "## A practical model-and-tool workflow" in text
    assert "inventory_demo" in text
    assert text.count("django_chat") == 1


def test_developer_doc_holds_moved_internals():
    text = _developer()
    assert "## Why openai-agents" in text
    assert "```mermaid" in text
    assert "BA" in text and "Engineer" in text and "Tester" in text
    assert "Skeptic" in text
    assert "ApiKindBase" in text
    assert "## Package layout" in text
    assert "## Dev setup, tests, CI" in text
    assert "## Gateway vs workers" in text
    assert "CONTRIBUTING.md" in text
    lowered = text.lower()
    for needle in ("sk-", "github_pat_", "ghp_"):
        assert needle not in lowered
    assert_no_private_ip(text)


def test_vision_points_at_current_readme_not_stale_466():
    """#782 skeptic nit: What remains points at #791, not unfinished README #466."""
    text = (repo_root() / "docs" / "VISION.md").read_text(encoding="utf-8")
    remains = text.split("## What remains", 1)[-1].split("## How the pieces fit", 1)[0]
    assert "#791" in remains
    assert "DEVELOPER.md" in remains
    assert "sibling rewrite" not in remains.lower()
    assert "unfinished" not in remains.lower()
    if "#466" in remains:
        assert "#785" in remains
        assert "not the old" in remains.lower() or "already landed" in remains.lower()
    assert "[README](../README.md)" in text or "[README.md](../README.md)" in text
    lowered = text.lower()
    for needle in ("sk-", "github_pat_", "ghp_"):
        assert needle not in lowered
