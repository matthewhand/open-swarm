from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint


def test_analyze_self_runs():
    ws = WhingeSurfBlueprint()
    result = ws.analyze_self(output_format="text")
    # Accept either 'Self-Analysis' or 'code analysis' or class name in output
    assert any(s in result for s in ("Self-Analysis", "code analysis", "WhingeSurfBlueprint"))
