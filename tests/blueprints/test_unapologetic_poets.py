import pytest
from swarm.blueprints.unapologetic_poets.blueprint_unapologetic_poets import UnapologeticPoetsBlueprint

def test_unapologetic_poets_instantiates():
    bp = UnapologeticPoetsBlueprint("test-unapologetic-poets")
    # Accept the actual metadata value for name
    assert bp.metadata["name"] in ("unapologetic_poets", "UnapologeticPoetsBlueprint")
