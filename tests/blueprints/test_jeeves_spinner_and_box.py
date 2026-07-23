"""Spinner tests for the Jeeves blueprint's JeevesSpinner.

(The shared display_operation_box rendering contract is covered once in
test_operation_box_shared.py, not duplicated here.)
"""
import pytest

from swarm.blueprints.jeeves.blueprint_jeeves import JeevesSpinner
from swarm.core.output_utils import print_operation_box as display_operation_box_core


@pytest.mark.parametrize("frame_idx,expected", [
    (0, "Generating."),
    (1, "Generating.."),
    (2, "Generating..."),
    (3, "Running..."),
    (4, JeevesSpinner.LONG_WAIT_MSG),
    (5, JeevesSpinner.SPINNER_STATES[0]),
])
def test_jeeves_spinner_frames(frame_idx, expected):
    spinner = JeevesSpinner()
    spinner.start()
    for _ in range(frame_idx):
        spinner._spin()
    assert spinner.current_spinner_state() == expected


def test_jeeves_spinner_long_wait():
    spinner = JeevesSpinner()
    spinner.start()
    spinner._start_time -= 15  # Simulate long wait
    spinner._spin()
    assert spinner.current_spinner_state() == "Generating... Taking longer than expected"