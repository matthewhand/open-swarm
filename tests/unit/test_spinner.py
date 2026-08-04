"""Tests for the canonical spinner implementation in swarm.core.spinner.

Historical note: this file previously tested the legacy swarm.ux.spinner
implementation, which is now a deprecation shim re-exporting the core
spinner (see ROADMAP.md sunset notes).
"""

import time

from swarm.core.spinner import Spinner


def test_spinner_disabled_when_not_interactive():
    spinner = Spinner(interactive=False)
    assert spinner.enabled is False
    spinner.start("Working")
    assert spinner.running is False
    # stop() on a never-started spinner is a no-op
    spinner.stop()
    assert spinner.running is False


def test_spinner_runs_and_stops():
    spinner = Spinner(interactive=True)
    spinner.enabled = True  # force-enable (pytest stdout is not a TTY)
    spinner.start("Working")
    assert spinner.running is True
    assert spinner.thread is not None and spinner.thread.is_alive()
    time.sleep(0.15)
    spinner.stop()
    assert spinner.running is False
    assert spinner.thread is None


def test_spinner_writes_status_messages(capsys):
    spinner = Spinner(interactive=True)
    spinner.enabled = True
    spinner.start("Crunching numbers")
    time.sleep(0.25)
    spinner.stop()
    out = capsys.readouterr().out
    assert "Crunching numbers" in out


def test_spinner_custom_sequence(capsys):
    spinner = Spinner(interactive=True, custom_sequence="generating")
    spinner.enabled = True
    spinner.start()
    time.sleep(0.5)
    spinner.stop()
    out = capsys.readouterr().out
    assert "Generating" in out


def test_ux_spinner_shim_reexports_core_spinner():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from swarm.ux.spinner import Spinner as ShimSpinner
    assert ShimSpinner is Spinner
