import pytest


@pytest.fixture(autouse=True)
def _isolate_dynamic_registry(tmp_path, monkeypatch):
    """Isolate dynamic team registry to a temp directory per-test and clear caches."""
    import swarm.views.utils as utils

    cfg_dir = tmp_path / "swarm_cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        utils, "get_user_config_dir_for_swarm", lambda: cfg_dir, raising=True
    )
    monkeypatch.setattr(
        utils, "ensure_swarm_directories_exist",
        lambda: cfg_dir.mkdir(exist_ok=True), raising=True
    )
    monkeypatch.setattr(utils, "_dynamic_registry", {}, raising=True)
    monkeypatch.setattr(utils, "_blueprint_meta_cache", None, raising=True)
    yield


@pytest.mark.asyncio
async def test_get_blueprint_instance_applies_llm_profile(monkeypatch):
    """Registered dynamic teams should propagate llm_profile to the instance property."""
    from swarm.views import utils

    # Only dynamic teams
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    utils.register_dynamic_team("team-pro", description="P", llm_profile="pro")
    inst = await utils.get_blueprint_instance("team-pro")
    assert inst is not None
    # Should be applied to the property on the instance
    assert inst.llm_profile_name == "pro"


@pytest.mark.asyncio
async def test_get_blueprint_instance_missing_returns_none(monkeypatch):
    from swarm.views import utils

    # Ensure discovery is empty so lookup fails
    monkeypatch.setattr(utils, "discover_blueprints", lambda *_: {}, raising=True)

    inst = await utils.get_blueprint_instance("nope")
    assert inst is None

