import time
from swarm.ux.spinner import Spinner

def test_spinner_runs_and_stops():
    spinner = Spinner(base_message='Running', long_wait_timeout=1)
    spinner.start()
    time.sleep(1.5)
    spinner.stop()
    # If no exceptions, spinner works.

def test_spinner_long_wait():
    spinner = Spinner(base_message='Generating', long_wait_timeout=0.5)
    spinner.start()
    time.sleep(1)
    spinner.stop()
    # Should switch to 'Taking longer than expected' after 0.5s
    # No assert: just check for no crash
