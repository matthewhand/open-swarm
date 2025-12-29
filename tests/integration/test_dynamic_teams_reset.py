import pytest
from asgiref.sync import async_to_sync

from src.swarm.views.utils import (
    get_available_blueprints,
    load_dynamic_registry,
    register_dynamic_team,
    reset_dynamic_registry,
)


@pytest.mark.django_db(transaction=True)
def test_reset_clears_dynamic_registry_and_discovery(settings):
    # Add a couple of teams
    register_dynamic_team("reset-a", description="A")
    register_dynamic_team("reset-b", description="B")

    reg = load_dynamic_registry()
    assert "reset-a" in reg and "reset-b" in reg

    # Reset
    reset_dynamic_registry()
    reg = load_dynamic_registry()
    assert not reg  # empty

    discovered = async_to_sync(get_available_blueprints)()
    assert isinstance(discovered, dict)
    assert "reset-a" not in discovered and "reset-b" not in discovered

