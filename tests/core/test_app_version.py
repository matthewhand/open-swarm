"""REQ-78 advertised app version. No secrets."""

from swarm.core.app_version import (
    _parse_pyproject_version,
    get_app_version,
)


def test_parse_pyproject_version():
    text = '[project]\nname = "open-swarm"\nversion = "0.5.4"\n'
    assert _parse_pyproject_version(text) == "0.5.4"


def test_parse_pyproject_version_ignores_noise():
    assert _parse_pyproject_version("name = 'x'\n") is None
    assert _parse_pyproject_version('version = ""\n') is None


def test_get_app_version_matches_pyproject():
    version = get_app_version()
    assert version
    assert version != "0.0.0"
    assert version[0].isdigit()
