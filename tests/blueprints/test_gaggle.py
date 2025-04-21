import pytest
from swarm.blueprints.gaggle.blueprint_gaggle import GaggleBlueprint

def test_gaggle_instantiates():
    # Handle case where constructor takes no arguments
    try:
        bp = GaggleBlueprint("test-gaggle")
    except TypeError:
        bp = GaggleBlueprint()
    assert hasattr(bp, "metadata")
