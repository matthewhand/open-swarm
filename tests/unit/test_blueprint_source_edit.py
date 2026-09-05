"""Unit tests for REQ-211 source validation and origin classification."""

import pytest

from swarm.core.blueprint_source import (
    ORIGIN_BUNDLED,
    ORIGIN_CUSTOM,
    ORIGIN_USER,
    resolve_blueprint_origin,
    validate_writable_source,
)


def test_validate_rejects_syntax_error():
    with pytest.raises(ValueError, match="Invalid Python syntax"):
        validate_writable_source("def (\n", "blueprint_x.py")


def test_validate_accepts_simple_module():
    validate_writable_source("class Ok:\n    pass\n", "blueprint_x.py")


def test_validate_skips_non_python():
    validate_writable_source("not python {", "README.md")


def test_bundled_origin_is_read_only_class():
    assert resolve_blueprint_origin("cli_fusion") == ORIGIN_BUNDLED


def test_user_origin_wins_over_missing_custom(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path))
    (tmp_path / "blueprints" / "user_recipe").mkdir(parents=True)
    (tmp_path / "blueprints" / "user_recipe" / "blueprint_user_recipe.py").write_text(
        "class Ok:\n    pass\n"
    )
    assert resolve_blueprint_origin("user_recipe") == ORIGIN_USER


def test_custom_origin(monkeypatch):
    monkeypatch.setattr(
        "swarm.views.api_views.get_user_blueprint_library",
        lambda: {"installed": [], "custom": [{"id": "mine", "code": "x = 1\n"}]},
    )
    assert resolve_blueprint_origin("mine") == ORIGIN_CUSTOM
