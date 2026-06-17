"""Skills: reusable, named capabilities a CLI agent can be given for a task.

A **skill** is a directory containing a ``SKILL.md`` file: YAML frontmatter
(``name``, ``description``) plus a markdown body of instructions. It may bundle
helper files (scripts, templates) alongside the markdown, which a write-mode CLI
can read and run via its own tools.

Skills are deliberately CLI-agnostic — the same skill applies to gemini, claude,
grok, or any other adapter, because "applying" a skill just prepends its
instructions to the user's task. This mirrors the agentic-CLI "skill"/"extension"
idea but keeps it portable across every CLI in the fusion catalog.

    from swarm.core import skills
    catalog = skills.discover_skills()          # {name: Skill}
    prompt = skills.apply_skill(catalog["conventional-commit"], "diff: ...")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default search root: a top-level ``skills/`` dir in the repo / install.
from swarm.core.paths import get_project_root_dir  # noqa: E402

SKILL_FILE = "SKILL.md"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class Skill:
    """One discovered skill."""

    name: str
    description: str
    instructions: str
    path: Path | None = None
    # Bundled non-SKILL.md files shipped with the skill (scripts, templates, …).
    assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "assets": list(self.assets),
            "path": str(self.path) if self.path else None,
        }


def parse_skill_md(text: str, *, name_hint: str | None = None) -> Skill:
    """Parse a ``SKILL.md`` string into a :class:`Skill`.

    Frontmatter ``name``/``description`` win; ``name`` falls back to
    ``name_hint`` (typically the directory name). Raises ``ValueError`` when no
    name can be determined.
    """
    meta: dict[str, Any] = {}
    body = text
    m = _FRONTMATTER_RE.match(text.lstrip("﻿"))
    if m:
        loaded = yaml.safe_load(m.group(1)) or {}
        if isinstance(loaded, dict):
            meta = loaded
        body = m.group(2)

    name = str(meta.get("name") or name_hint or "").strip()
    if not name:
        raise ValueError("skill has no 'name' (frontmatter or directory name)")
    return Skill(
        name=name,
        description=str(meta.get("description") or "").strip(),
        instructions=body.strip(),
    )


def load_skill(skill_dir: Path) -> Skill:
    """Load a single skill from a directory containing ``SKILL.md``."""
    md = skill_dir / SKILL_FILE
    if not md.is_file():
        raise FileNotFoundError(f"no {SKILL_FILE} in {skill_dir}")
    skill = parse_skill_md(md.read_text(), name_hint=skill_dir.name)
    skill.path = skill_dir
    skill.assets = sorted(
        p.name for p in skill_dir.iterdir() if p.is_file() and p.name != SKILL_FILE
    )
    return skill


def skills_root() -> Path:
    """Default skills directory (``<project_root>/skills``)."""
    return Path(get_project_root_dir()) / "skills"


def discover_skills(root: str | Path | None = None) -> dict[str, Skill]:
    """Discover every skill under ``root`` (default: ``skills_root()``).

    A skill is any directory holding a ``SKILL.md``. Returns ``{name: Skill}``;
    malformed skills are skipped (never raises). Names are de-duplicated by
    first-wins on a sorted directory walk for determinism.
    """
    base = Path(root) if root is not None else skills_root()
    found: dict[str, Skill] = {}
    if not base.is_dir():
        return found
    for md in sorted(base.rglob(SKILL_FILE)):
        try:
            skill = load_skill(md.parent)
        except (ValueError, OSError):
            continue
        found.setdefault(skill.name, skill)
    return found


def apply_skill(skill: Skill, task: str) -> str:
    """Compose a prompt that gives a CLI agent ``skill`` for ``task``.

    Prepends the skill's instructions (and a note about any bundled assets, which
    a write-mode CLI can open in its workdir) ahead of the user's task.
    """
    parts = [f"You have been given the \"{skill.name}\" skill.", ""]
    if skill.description:
        parts += [skill.description, ""]
    parts += ["--- SKILL INSTRUCTIONS ---", skill.instructions, ""]
    if skill.assets:
        parts += [
            "This skill ships these files in your working directory; read or run "
            "them with your tools as needed: " + ", ".join(skill.assets),
            "",
        ]
    parts += ["--- TASK ---", task]
    return "\n".join(parts)
