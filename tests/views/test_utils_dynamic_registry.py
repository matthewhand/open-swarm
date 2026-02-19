import json

import pytest


@pytest.fixture(autouse=True)
def _isolate_dynamic_registry(tmp_path, monkeypatch):
    """Isolate dynamic team registry to a temp directory per-test.

    Patches utils to write its teams.json under tmp_path and resets in-memory caches.
    """
    import swarm.views.utils as utils

    # Point utils to a temporary config dir
    cfg_dir = tmp_path / "swarm_cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        utils, "get_user_config_dir_for_swarm", lambda: cfg_dir, raising=True
    )
    monkeypatch.setattr(
        utils, "ensure_swarm_directories_exist",
        lambda: cfg_dir.mkdir(exist_ok=True), raising=True
    )

    # Reset in-memory caches between tests
    monkeypatch.setattr(utils, "_dynamic_registry", {}, raising=True)
    monkeypatch.setattr(utils, "_blueprint_meta_cache", None, raising=True)

    yield


def _read_registry_file(tmp_path) -> dict:
    teams_path = tmp_path / "swarm_cfg" / "teams.json"
    if not teams_path.exists():
        return {}
    return json.loads(teams_path.read_text(encoding="utf-8"))


def test_register_and_persist_dynamic_team(tmp_path):
    """Test dynamic team registration and persistence with comprehensive validation"""
    from swarm.views.utils import load_dynamic_registry, register_dynamic_team

    # Register team with comprehensive parameters
    team_name = "alpha-team"
    team_description = "Alpha testing team"
    team_profile = "default"

    register_dynamic_team(
        team_name, description=team_description, llm_profile=team_profile
    )

    # In-memory view validation
    reg = load_dynamic_registry()
    assert team_name in reg, f"Team '{team_name}' should be in registry"
    assert reg[team_name]["description"] == team_description, "Description should match"
    assert reg[team_name]["llm_profile"] == team_profile, "LLM profile should match"

    # Validate team structure
    team_data = reg[team_name]
    assert isinstance(team_data, dict), "Team data should be a dictionary"
    assert "description" in team_data, "Team should have description field"
    assert "llm_profile" in team_data, "Team should have llm_profile field"
    assert len(team_data) >= 2, "Team should have at least description and llm_profile"

    # On-disk persistence validation
    disk = _read_registry_file(tmp_path)
    assert team_name in disk, f"Team '{team_name}' should be persisted to disk"
    assert (
        disk[team_name]["description"] == team_description
    ), "Persisted description should match"
    assert (
        disk[team_name]["llm_profile"] == team_profile
    ), "Persisted LLM profile should match"

    # Validate disk persistence structure
    disk_team_data = disk[team_name]
    assert disk_team_data == team_data, "Disk data should match in-memory data"


def test_duplicate_register_overwrites(tmp_path):
    from swarm.views.utils import load_dynamic_registry, register_dynamic_team

    register_dynamic_team("dupe", description="v1", llm_profile="p1")
    register_dynamic_team("dupe", description="v2", llm_profile="p2")
    reg = load_dynamic_registry()
    assert reg["dupe"]["description"] == "v2"
    assert reg["dupe"]["llm_profile"] == "p2"


def test_deregister_updates_state_and_disk(tmp_path):
    from swarm.views.utils import deregister_dynamic_team, register_dynamic_team

    # Remove non-existent -> False
    assert deregister_dynamic_team("ghost") is False

    register_dynamic_team("to-remove", description="X")
    assert deregister_dynamic_team("to-remove") is True
    assert "to-remove" not in _read_registry_file(tmp_path)
    # Second removal is a no-op
    assert deregister_dynamic_team("to-remove") is False


@pytest.mark.django_db
def test_available_blueprints_merge_in_dynamic(monkeypatch):
    from swarm.views import utils

    # Avoid scanning file system; return no static blueprints
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team(
        "demo-api-team", description="API Demo", llm_profile="default"
    )

    # Force build and fetch
    from asgiref.sync import async_to_sync
    available = async_to_sync(utils.get_available_blueprints)()
    assert available is not None
    assert "demo-api-team" in available
    info = available["demo-api-team"]
    # Class should be the dynamic team blueprint
    from swarm.blueprints.dynamic_team.blueprint_dynamic_team import (
        DynamicTeamBlueprint,
    )
    # Module aliasing may load via 'swarm.' vs 'src.swarm.'; compare by name to
    # avoid identity mismatch.
    assert info["class_type"].__name__ == DynamicTeamBlueprint.__name__
    assert "name" in info["metadata"]
    assert info["metadata"]["name"] == "demo-api-team"


@pytest.mark.asyncio
async def test_get_blueprint_instance_caching(monkeypatch):
    from swarm.views import utils

    # Simplify discovery to empty so only dynamic teams exist
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team("cache-team", description="C", llm_profile="default")

    # First call (no params) caches instance
    a = await utils.get_blueprint_instance("cache-team")
    b = await utils.get_blueprint_instance("cache-team")
    assert a is b

    # With params -> not cached; should be a distinct instance
    c = await utils.get_blueprint_instance("cache-team", params={"x": 1})
    assert c is not None and c is not a


def test_validate_model_access_respects_registry(monkeypatch):
    from swarm.views import utils

    # Avoid heavy discovery
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team("perm-team")
    assert utils.validate_model_access(user=None, model_name="perm-team") is True

    utils.deregister_dynamic_team("perm-team")
    assert utils.validate_model_access(user=None, model_name="perm-team") is False
