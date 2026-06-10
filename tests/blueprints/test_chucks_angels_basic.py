def test_import_blueprint():
    from swarm.blueprints.chucks_angels.blueprint_chucks_angels import (
        ChucksAngelsBlueprint,
    )
    assert ChucksAngelsBlueprint is not None
