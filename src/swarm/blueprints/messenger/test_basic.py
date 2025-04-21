def test_import_blueprint():
    from .blueprint_messenger import MessengerBlueprint
    assert MessengerBlueprint is not None
