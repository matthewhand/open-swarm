import time
from swarm.ux.spinner import Spinner


def test_spinner_runs_and_stops():
    spinner = Spinner(base_message="Running", long_wait_timeout=0.2)
    spinner.start()
    assert spinner.running is True
    time.sleep(0.3)
    spinner.stop()
    assert spinner.running is False
    assert spinner.thread is not None
    assert not spinner.thread.is_alive()


def test_spinner_long_wait_state_transition():
    spinner = Spinner(base_message="Generating", long_wait_timeout=0.2)
    spinner.start()
    time.sleep(0.5)
    # After timeout elapses, internal long-wait flag should be set
    assert spinner._long_wait is True  # noqa: SLF001 (intentional: validate behavior)
    spinner.stop()


def test_set_message_resets_long_wait():
    spinner = Spinner(base_message="Generating", long_wait_timeout=0.2)
    spinner.start()
    time.sleep(0.5)
    assert spinner._long_wait is True  # noqa: SLF001
    # Changing the message should reset long-wait state
    spinner.set_message("New Task")
    assert spinner.base_message == "New Task"
    assert spinner._long_wait is False  # noqa: SLF001
    # It should transition back to long-wait after the timeout again
    time.sleep(0.5)
    assert spinner._long_wait is True  # noqa: SLF001
    spinner.stop()


def test_spinner_writes_status_messages(capsys):
    spinner = Spinner(base_message="Working", long_wait_timeout=0.2)
    spinner.start()
    time.sleep(0.25)
    # Capture early output showing animated states (e.g., Working.)
    early = capsys.readouterr().out
    assert "Working" in early
    # Wait long enough to trigger the long-wait message
    time.sleep(0.5)
    spinner.stop()
    out = capsys.readouterr().out
    combined = early + out
    assert "Working" in combined
    assert "Taking longer than expected" in combined
