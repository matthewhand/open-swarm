"""Compact service-level summary, without URLs, credentials or transcripts."""
from collections import defaultdict

import pytest

_results = defaultdict(dict)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    report = outcome.get_result()
    if "live_remote" in item.keywords and report.when == "call":
        params = item.callspec.params
        _results[params["instance"]][params["phase"]] = report.outcome


def pytest_terminal_summary(terminalreporter):
    if not _results:
        return
    terminalreporter.section("Live remote integration results (completed inference required)")
    working = configured = 0
    for name, phases in sorted(_results.items()):
        active = any(value != "skipped" for value in phases.values())
        configured += active
        working += all(phases.get(key) == "passed" for key in ("health", "discovery", "inference"))
        terminalreporter.write_line(name + ": " + ", ".join(f"{key}={value}" for key, value in sorted(phases.items())))
    terminalreporter.write_line(f"Working integrations: {working}/{configured} configured; {len(_results)-configured} unconfigured")
