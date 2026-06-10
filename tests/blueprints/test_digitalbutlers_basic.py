def test_import_blueprint():
    from swarm.blueprints.digitalbutlers.blueprint_digitalbutlers import (
        DigitalButlersBlueprint,
    )
    assert DigitalButlersBlueprint is not None
