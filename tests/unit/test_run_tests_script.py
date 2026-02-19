import importlib
import os
import sys
from types import ModuleType


def _reload_run_tests(monkeypatch):
    """Reload the run_tests module fresh for each scenario."""
    # Ensure a clean import (module caches env at import-time in some cases)
    if "scripts.run_tests" in sys.modules:
        del sys.modules["scripts.run_tests"]
    return importlib.import_module("scripts.run_tests")


def test_env_defaults_are_set(monkeypatch):
    # Start with a clean environment
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.delenv("DJANGO_ALLOW_ASYNC_UNSAFE", raising=False)
    monkeypatch.delenv("DJANGO_TEST_DB_NAME", raising=False)

    # Stub pytest.main so we don't actually run pytest from within pytest
    calls = {}

    class DummyPyTest(ModuleType):
        def main(self, args):
            calls["args"] = list(args)
            return 0

    monkeypatch.setitem(sys.modules, "pytest", DummyPyTest("pytest"))
    # Ensure pytest_cov is absent for this scenario
    monkeypatch.setitem(sys.modules, "pytest_cov", None)

    run_tests = _reload_run_tests(monkeypatch)
    exit_code = run_tests.main()

    assert exit_code == 0
    # Env defaults should be set by the script
    assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
    assert os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE") == "true"
    assert os.environ.get("DJANGO_TEST_DB_NAME") == ":memory:"

    # Plugins explicitly enabled (in order appended by script)
    assert calls["args"][:6] == ["-p", "django", "-p", "asyncio", "-p", "pytest_mock"]


def test_includes_pytest_cov_when_available(monkeypatch):
    # Clean env to avoid interference
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.delenv("DJANGO_ALLOW_ASYNC_UNSAFE", raising=False)
    monkeypatch.delenv("DJANGO_TEST_DB_NAME", raising=False)

    calls = {}

    class DummyPyTest(ModuleType):
        def main(self, args):
            calls["args"] = list(args)
            return 0

    # Provide pytest and a dummy pytest_cov module to simulate availability
    monkeypatch.setitem(sys.modules, "pytest", DummyPyTest("pytest"))
    monkeypatch.setitem(sys.modules, "pytest_cov", ModuleType("pytest_cov"))

    run_tests = _reload_run_tests(monkeypatch)
    exit_code = run_tests.main()

    assert exit_code == 0
    # Ensure pytest-cov plugin is explicitly loaded
    # It should appear after the base three plugins
    assert ["-p", "pytest_cov"] in [calls["args"][i : i + 2] for i in range(len(calls["args"]) - 1)]


def test_forwards_cli_args(monkeypatch):
    # Prepare dummy pytest
    calls = {}

    class DummyPyTest(ModuleType):
        def main(self, args):
            calls["args"] = list(args)
            return 0

    monkeypatch.setitem(sys.modules, "pytest", DummyPyTest("pytest"))
    # Remove pytest_cov to keep expectations simple
    monkeypatch.setitem(sys.modules, "pytest_cov", None)

    # Simulate passing through additional pytest args
    argv_backup = list(sys.argv)
    try:
        sys.argv = [argv_backup[0], "-q", "-k", "dummy_selection"]
        run_tests = _reload_run_tests(monkeypatch)
        exit_code = run_tests.main()
        assert exit_code == 0
        # The forwarded args should be preserved (order among themselves retained)
        calls["args"][calls["args"].index("-q") : ] if "-q" in calls["args"] else calls["args"]
        # Ensure '-k' is present and immediately followed by the selection
        assert "-k" in calls["args"]
        k_index = calls["args"].index("-k")
        assert calls["args"][k_index + 1] == "dummy_selection"
        # Ensure quiet flag is included among forwarded args
        assert "-q" in calls["args"]
    finally:
        sys.argv = argv_backup
