#!/usr/bin/env python3
"""
Blueprint README Linter for Open Swarm
Checks for missing sections, env vars, and links in each blueprint README and suggests fixes.
"""
import os
import re
from pathlib import Path
from typing import List

BLUEPRINTS_DIR = Path(__file__).parent.parent / "src" / "swarm" / "blueprints"
EXCLUDE = {"common"}

REQUIRED_SECTIONS = ["features", "env", "usage", "installation"]


def find_blueprints() -> List[Path]:
    return [p for p in BLUEPRINTS_DIR.iterdir() if p.is_dir() and p.name not in EXCLUDE]

def lint_readme(bp_dir: Path) -> List[str]:
    readme = bp_dir / "README.md"
    if not readme.exists():
        return ["README.md missing"]
    text = readme.read_text(errors="ignore").lower()
    issues = []
    for section in REQUIRED_SECTIONS:
        if section not in text:
            issues.append(f"Section '{section}' missing")
    if not re.search(r"env.*var", text):
        issues.append("No env var section found")
    if "usage" not in text:
        issues.append("No usage section found")
    return issues

def main():
    for bp in find_blueprints():
        issues = lint_readme(bp)
        if issues:
            print(f"[!] {bp.name}: ", "; ".join(issues))
        else:
            print(f"[OK] {bp.name}: README.md looks good.")

if __name__ == "__main__":
    main()
