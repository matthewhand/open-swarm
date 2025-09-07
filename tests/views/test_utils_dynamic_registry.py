import json

import pytest


@pytest.fixture(autouse=True)
def _isolate_dynamic_registry(tmp_path, monkeypatch):
    """Isolate dynamic team registry to a temp directory per-test.

    Patches utils to write its teams.json under tmp_path and resets in-memory caches.
    """
    import src.swarm.views.utils as utils

    # Point utils to a temporary config dir
    cfg_dir = tmp_path / "swarm_cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(utils, "get_user_config_dir_for_swarm", lambda: cfg_dir, raising=True)
    monkeypatch.setattr(utils, "ensure_swarm_directories_exist", lambda: cfg_dir.mkdir(exist_ok=True), raising=True)

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
    from src.swarm.views.utils import load_dynamic_registry, register_dynamic_team

    register_dynamic_team("alpha-team", description="Alpha", llm_profile="default")

    # In-memory view
    reg = load_dynamic_registry()
    assert "alpha-team" in reg
    assert reg["alpha-team"]["description"] == "Alpha"
    assert reg["alpha-team"]["llm_profile"] == "default"

    # On-disk persistence
    disk = _read_registry_file(tmp_path)
    assert "alpha-team" in disk


def test_duplicate_register_overwrites(tmp_path):
    from src.swarm.views.utils import load_dynamic_registry, register_dynamic_team

    register_dynamic_team("dupe", description="v1", llm_profile="p1")
    register_dynamic_team("dupe", description="v2", llm_profile="p2")
    reg = load_dynamic_registry()
    assert reg["dupe"]["description"] == "v2"
    assert reg["dupe"]["llm_profile"] == "p2"


def test_deregister_updates_state_and_disk(tmp_path):
    from src.swarm.views.utils import deregister_dynamic_team, register_dynamic_team

    # Remove non-existent -> False
    assert deregister_dynamic_team("ghost") is False

    register_dynamic_team("to-remove", description="X")
    assert deregister_dynamic_team("to-remove") is True
    assert "to-remove" not in _read_registry_file(tmp_path)
    # Second removal is a no-op
    assert deregister_dynamic_team("to-remove") is False


@pytest.mark.django_db
def test_available_blueprints_merge_in_dynamic(monkeypatch):
    from src.swarm.views import utils

    # Avoid scanning file system; return no static blueprints
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team("demo-api-team", description="API Demo", llm_profile="default")

    # Force build and fetch
    from asgiref.sync import async_to_sync
    available = async_to_sync(utils.get_available_blueprints)()
    assert "demo-api-team" in available
    info = available["demo-api-team"]
    # Class should be the dynamic team blueprint
    from src.swarm.blueprints.dynamic_team.blueprint_dynamic_team import (
        DynamicTeamBlueprint,
    )
    # Module aliasing may load via 'swarm.' vs 'src.swarm.'; compare by name to avoid identity mismatch.
    assert info["class_type"].__name__ == DynamicTeamBlueprint.__name__
    assert info["metadata"]["name"] == "demo-api-team"


@pytest.mark.asyncio
async def test_get_blueprint_instance_caching(monkeypatch):
    from src.swarm.views import utils

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
    from src.swarm.views import utils

    # Avoid heavy discovery
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team("perm-team")
    assert utils.validate_model_access(user=None, model_name="perm-team") is True

    utils.deregister_dynamic_team("perm-team")
    assert utils.validate_model_access(user=None, model_name="perm-team") is False
