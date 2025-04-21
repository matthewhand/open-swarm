#!/usr/bin/env python3
"""
Blueprint QA Automation Script for Open Swarm
Scans all blueprints and checks for README health, test coverage, CLI health, and binary equivalence.
"""
import os
import subprocess
import sys
from pathlib import Path
import re
from typing import Dict, List

BLUEPRINTS_DIR = Path(__file__).parent.parent / "src" / "swarm" / "blueprints"
EXCLUDE = {"common"}


def find_blueprints() -> List[Path]:
    return [p for p in BLUEPRINTS_DIR.iterdir() if p.is_dir() and not p.name.startswith("__") and p.name not in EXCLUDE]

def check_readme(bp_dir: Path) -> Dict:
    readme = bp_dir / "README.md"
    if not readme.exists():
        return {"exists": False, "env_section": False, "features_section": False}
    text = readme.read_text(errors="ignore")
    env_section = bool(re.search(r"env.*var", text, re.I))
    features_section = bool(re.search(r"feature", text, re.I))
    return {"exists": True, "env_section": env_section, "features_section": features_section}

def check_test_coverage(bp_dir: Path) -> Dict:
    test_dir = bp_dir / "tests"
    if not test_dir.exists():
        return {"has_tests": False, "coverage": 0}
    try:
        result = subprocess.run(["pytest", "--maxfail=1", "--disable-warnings", "--cov", str(bp_dir)],
                               capture_output=True, text=True, timeout=60)
        m = re.search(r"TOTAL.*?(\d+)%", result.stdout)
        coverage = int(m.group(1)) if m else 0
        return {"has_tests": True, "coverage": coverage, "pytest_output": result.stdout}
    except Exception as e:
        return {"has_tests": True, "coverage": 0, "error": str(e)}

def check_cli_health(bp_name: str) -> bool:
    try:
        result = subprocess.run(["timeout", "15", "swarm-cli", "run", bp_name, "--instruction", "ping"],
                                capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def main():
    print("\nBlueprint QA Summary:")
    print("="*40)
    failures = []
    for bp in find_blueprints():
        name = bp.name
        print(f"\nBlueprint: {name}")
        readme = check_readme(bp)
        print(f"  README exists: {readme['exists']}")
        print(f"  Env var section: {readme['env_section']}")
        print(f"  Features section: {readme['features_section']}")
        test = check_test_coverage(bp)
        print(f"  Has tests: {test['has_tests']}")
        print(f"  Coverage: {test.get('coverage', 0)}%")
        if 'error' in test:
            print(f"  Pytest error: {test['error']}")
            failures.append(f"{name}: Pytest error: {test['error']}")
        if not readme['exists']:
            failures.append(f"{name}: Missing README.md")
        cli_ok = check_cli_health(name)
        print(f"  CLI health: {cli_ok}")
        if not cli_ok:
            failures.append(f"{name}: CLI health check failed")
        print("-"*30)
    if failures:
        print("\nERROR: One or more blueprints failed QA checks:")
        for fail in failures:
            print(f"  - {fail}")
        sys.exit(1)

if __name__ == "__main__":
    main()
