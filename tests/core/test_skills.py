"""Tests for the skills core (discovery, parsing, prompt composition)."""
from pathlib import Path

import pytest

from swarm.core import skills

SKILL_MD = """---
name: haiku
description: Reply with a 5-7-5 haiku.
---
Respond with exactly three lines forming a 5-7-5 haiku. No other text.
"""


def test_parse_skill_md_reads_frontmatter_and_body():
    s = skills.parse_skill_md(SKILL_MD)
    assert s.name == "haiku"
    assert s.description == "Reply with a 5-7-5 haiku."
    assert s.instructions.startswith("Respond with exactly three lines")
    assert "---" not in s.instructions


def test_parse_skill_md_name_falls_back_to_hint():
    s = skills.parse_skill_md("just a body, no frontmatter", name_hint="my-skill")
    assert s.name == "my-skill"
    assert s.instructions == "just a body, no frontmatter"


def test_parse_skill_md_without_name_raises():
    with pytest.raises(ValueError):
        skills.parse_skill_md("body only, no frontmatter, no hint")


def test_discover_skills_finds_skill_dirs(tmp_path: Path):
    d = tmp_path / "haiku"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_MD)
    (d / "helper.py").write_text("print('hi')\n")

    found = skills.discover_skills(tmp_path)
    assert set(found) == {"haiku"}
    assert found["haiku"].assets == ["helper.py"]
    assert found["haiku"].path == d


def test_discover_skills_skips_malformed(tmp_path: Path):
    # A SKILL.md with no body (no instructions) is malformed → skipped.
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "SKILL.md").write_text("---\nname: empty\ndescription: x\n---\n")
    good = tmp_path / "ok"
    good.mkdir()
    (good / "SKILL.md").write_text(SKILL_MD)

    found = skills.discover_skills(tmp_path)
    assert "haiku" in found
    assert "empty" not in found


def test_discover_skills_missing_root_is_empty(tmp_path: Path):
    assert skills.discover_skills(tmp_path / "nope") == {}


def test_apply_skill_injects_instructions_and_task():
    s = skills.parse_skill_md(SKILL_MD)
    prompt = skills.apply_skill(s, "Write about autumn.")
    assert "haiku" in prompt
    assert "SKILL INSTRUCTIONS" in prompt
    assert "5-7-5 haiku" in prompt
    assert prompt.rstrip().endswith("Write about autumn.")


def test_apply_skill_mentions_assets_when_present():
    s = skills.Skill(name="x", description="", instructions="do x", assets=["run.py"])
    prompt = skills.apply_skill(s, "go")
    assert "run.py" in prompt


def test_bundled_conventional_commit_skill_is_discoverable():
    # The repo ships at least this skill under <root>/skills.
    found = skills.discover_skills()
    assert "conventional-commit" in found
    assert found["conventional-commit"].description
