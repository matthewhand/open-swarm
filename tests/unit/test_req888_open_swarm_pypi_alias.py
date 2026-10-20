"""REQ-888 / #296 — PyPI `open-swarm` is a deprecation alias, not the product.

Product wheel is `os-core`. This stub lives in-tree at packaging/open-swarm-alias/.
Publish of the stub is operator-only after `os-core` exists on PyPI; do not yank 0.5.4.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STUB = REPO / "packaging" / "open-swarm-alias"
PYPROJECT = STUB / "pyproject.toml"
README = STUB / "README.md"


def _data() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _project() -> dict:
    return _data()["project"]


def test_stub_pyproject_prerelease_version_and_inactive_classifier():
    from packaging.version import Version
    project = _project()
    core = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "open-swarm"
    assert Version(project["version"]) == Version(core["version"])
    assert Version(project["version"]) > Version("0.5.4")
    assert Version(project["version"]).is_prerelease
    assert "Development Status :: 7 - Inactive" in project["classifiers"]


def test_stub_depends_on_matching_core_prerelease_with_a_bounded_series():
    from packaging.requirements import Requirement
    core = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = [Requirement(dep) for dep in _project()["dependencies"]]
    assert len(dependencies) == 1
    requirement = dependencies[0]
    assert requirement.name == "os-core"
    assert core["version"] in requirement.specifier
    assert "0.5.4" not in requirement.specifier
    assert "0.7" not in requirement.specifier


def test_stub_pyproject_does_not_define_swarm_cli_or_other_scripts():
    data = _data()
    project = data["project"]
    scripts = project.get("scripts") or {}
    assert "swarm-cli" not in scripts
    assert "os-cli" not in scripts
    assert "os-api" not in scripts
    assert scripts == {}
    raw = PYPROJECT.read_text(encoding="utf-8")
    assert "[project.scripts]" not in raw
    assert "swarm-cli" not in raw


def test_stub_readme_is_rename_banner_not_full_product():
    text = README.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "operating swarm" in lowered
    assert "os-core" in text
    assert "https://github.com/matthewhand/operating-swarm" in text
    assert "open-swarm" in lowered
    assert "deprecated" in lowered or "deprecation" in lowered or "alias" in lowered
    assert not (STUB / "src" / "swarm").exists()
    # Stub is not a second copy of the app README.
    assert "## Kinds (locked)" not in text
    assert "WebUI is first-class" not in text
