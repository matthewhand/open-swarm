"""Skills: reusable, named capabilities a CLI agent can be given for a task.

A **skill** is a directory containing a ``SKILL.md`` file: YAML frontmatter
(``name``, ``description``) plus a markdown body of instructions. It may bundle
helper files (scripts, templates) alongside the markdown, which a write-mode CLI
can read and run via its own tools.

Skills are deliberately CLI-agnostic — the same skill applies to gemini, claude,
grok, or any other adapter, because "applying" a skill just prepends its
instructions to the user's task. This mirrors the agentic-CLI "skill"/"extension"
idea but keeps it portable across every CLI in the fusion catalog.

The SKILL.md format and the name/description validation follow Anthropic's
`Agent Skills <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>`_
open standard, so skills authored here also load in Claude Code and the Skills
API unchanged.

    from swarm.core import skills
    catalog = skills.discover_skills()          # {name: Skill}
    prompt = skills.apply_skill(catalog["conventional-commit"], "diff: ...")
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default search root: a top-level ``skills/`` dir in the repo / install.
from swarm.core.paths import get_project_root_dir  # noqa: E402

SKILL_FILE = "SKILL.md"

# Frontmatter + validation follow Anthropic's Agent Skills open standard so our
# skills are portable to Claude Code / the Skills API:
#   name        — 1-64 chars, lowercase letters/digits/hyphens, no reserved words
#   description — non-empty (recommended), <= 1024 chars; says what + when
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
_RESERVED_WORDS = ("anthropic", "claude")
MAX_DESCRIPTION = 1024


@dataclass
class Skill:
    """One discovered skill."""

    name: str
    description: str
    instructions: str
    path: Path | None = None
    # Bundled non-SKILL.md files shipped with the skill (scripts, templates, …).
    assets: list[str] = field(default_factory=list)


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
    if not _NAME_RE.match(name):
        raise ValueError(
            f"skill name '{name}' must be 1-64 chars of lowercase letters, digits, or hyphens"
        )
    if any(w in name for w in _RESERVED_WORDS):
        raise ValueError(f"skill name '{name}' may not contain reserved words {_RESERVED_WORDS}")

    description = str(meta.get("description") or "").strip()
    if len(description) > MAX_DESCRIPTION:
        raise ValueError(f"skill '{name}' description exceeds {MAX_DESCRIPTION} chars")

    instructions = body.strip()
    if not instructions:
        raise ValueError(f"skill '{name}' has no instructions (empty SKILL.md body)")
    return Skill(name=name, description=description, instructions=instructions)


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


def stage_assets(skill: Skill, workdir: str | Path) -> list[str]:
    """Copy a skill's bundled asset files into ``workdir``.

    A skill can ship scripts/templates alongside SKILL.md; ``apply_skill`` only
    *names* them, so they must be placed in the CLI's working directory for a
    write-mode CLI to read or execute. Returns the staged filenames. No-op when
    the skill has no path on disk or no assets.
    """
    if not skill.path or not skill.assets:
        return []
    dest = Path(workdir)
    dest.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for name in skill.assets:
        src = skill.path / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            staged.append(name)
    return staged
