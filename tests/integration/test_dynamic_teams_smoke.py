import pytest
from asgiref.sync import async_to_sync

from src.swarm.views.utils import (
    register_dynamic_team,
    deregister_dynamic_team,
    get_available_blueprints,
    load_dynamic_registry,
)


@pytest.mark.django_db(transaction=True)
def test_dynamic_team_registry_and_discovery_roundtrip(settings):
    # Ensure clean slate
    deregister_dynamic_team("demo-team")

    # Register a team
    register_dynamic_team("demo-team", description="Demo dynamic team", llm_profile="default")

    # Confirm persisted
    reg = load_dynamic_registry()
    assert "demo-team" in reg

    # Confirm discovery sees it
    discovered = async_to_sync(get_available_blueprints)()
    assert isinstance(discovered, dict)
    assert "demo-team" in discovered

    # Cleanup
    assert deregister_dynamic_team("demo-team") is True
