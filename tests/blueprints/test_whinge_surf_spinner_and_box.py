import pytest
import time
from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSpinner, WhingeSurfBlueprint
from swarm.blueprints.common.operation_box_utils import display_operation_box

def test_whinge_spinner_states():
    spinner = WhingeSpinner()
    spinner.start()
    states = []
    for _ in range(6):
        spinner._spin()
        states.append(spinner.current_spinner_state())
    assert states[:3] == ["Generating..", "Generating...", "Running..."]
    spinner._start_time -= 11
    assert spinner.current_spinner_state() == spinner.LONG_WAIT_MSG

def test_whinge_operation_box_output(capsys):
    spinner = WhingeSpinner()
    spinner.start()
    display_operation_box(
        title="Whinge Test",
        content="Testing operation box",
        spinner_state=spinner.current_spinner_state(),
        emoji="🌊"
    )
    captured = capsys.readouterr()
    assert "Whinge Test" in captured.out
    assert "Testing operation box" in captured.out
    assert "🌊" in captured.out

def test_whinge_job_status(monkeypatch, capsys):
    blueprint = WhingeSurfBlueprint()
    blueprint.spinner.start()
    blueprint._display_job_status("123", "Running", output="step output", progress=3, total=5)
    captured = capsys.readouterr()
    assert "WhingeSurf Job 123" in captured.out
    assert "Status: Running" in captured.out
    assert "step output" in captured.out
