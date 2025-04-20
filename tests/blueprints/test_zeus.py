from swarm.blueprints.zeus.blueprint_zeus import ZeusCoordinatorBlueprint as DivineAssistantBlueprint

def test_metadata_lists_cli_as_divine_ass():
    meta = DivineAssistantBlueprint.get_metadata()
    assert meta["cli"] == "zeus"
    assert meta["name"] == "zeus"
    assert "coordinator" in meta["description"].lower()
