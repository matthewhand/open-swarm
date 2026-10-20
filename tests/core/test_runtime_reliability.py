"""Regression coverage for installation and real-turn failures found in review."""
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from swarm.core.kind_bases import ApiKindBase


def test_test_environment_has_private_config_and_data_roots(tmp_path):
    from swarm.core.paths import config_root, get_user_data_dir_for_swarm
    assert config_root().is_relative_to(tmp_path)
    assert get_user_data_dir_for_swarm().is_relative_to(tmp_path)


def test_skill_files_use_utf8_on_windows_too(tmp_path):
    from swarm.core.skills import load_skill
    folder = tmp_path / "unicode-demo"
    folder.mkdir()
    (folder / "SKILL.md").write_text(
        "---\nname: unicode-demo\ndescription: UTF-8 example.\n---\nReview 漢字 and \u200d text.\n",
        encoding="utf-8")
    assert "漢字" in load_skill(folder).instructions


def test_explicit_config_root_never_imports_home_config(tmp_path, monkeypatch):
    from swarm.core.paths import startup_should_migrate_config
    monkeypatch.setenv("SWARM_CONFIG_DIR", str(tmp_path / "isolated"))
    monkeypatch.setenv("SWARM_ALLOW_CONFIG_MIGRATE_IN_TESTS", "1")
    assert startup_should_migrate_config() is False


class Demo(ApiKindBase):
    metadata = {"name": "reliability_demo"}

    def create_starting_agent(self, _mcp_servers=None):
        from agents import Agent
        return Agent(name="demo", model="test-model")


@pytest.mark.asyncio
async def test_runner_receives_prior_turns(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    run = AsyncMock(return_value=SimpleNamespace(final_output="remembered"))
    monkeypatch.setattr("agents.Runner.run", run)
    history = [{"role": "user", "content": "Remember notebooks."},
               {"role": "assistant", "content": "I will."},
               {"role": "user", "content": "What item?"}]
    chunks = [chunk async for chunk in Demo(blueprint_id="reliability_demo", config={}).run(history)]
    assert run.call_args.args[1] == history
    assert chunks[-1]["messages"][0]["content"] == "remembered"


@pytest.mark.asyncio
async def test_setup_failure_is_final_and_does_not_expose_credentials(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    def fail(*_args):
        raise ValueError("Bearer private-test-credential")
    monkeypatch.setattr(Demo, "create_starting_agent", fail)
    chunks = [chunk async for chunk in Demo(blueprint_id="reliability_demo", config={}).run([{"role":"user", "content":"hi"}])]
    assert chunks[-1]["error"] == "agent_setup_failed"
    assert chunks[-1]["final"] is True
    assert "private-test-credential" not in str(chunks)


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code", [(RuntimeError("private-test-credential"), "agent_execution_failed"),
                                       (TimeoutError(), "agent_timeout")])
async def test_run_failure_is_final_and_safe(monkeypatch, error, code):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    monkeypatch.setattr("agents.Runner.run", AsyncMock(side_effect=error))
    chunks = [chunk async for chunk in Demo(blueprint_id="reliability_demo", config={}).run([{"role":"user", "content":"hi"}])]
    assert chunks[-1]["error"] == code
    assert chunks[-1]["final"] is True
    assert "private-test-credential" not in str(chunks)


def test_cli_propagates_child_failure(tmp_path, monkeypatch):
    from swarm.core import swarm_cli
    script = tmp_path / "broken.py"
    script.write_text("raise SystemExit(7)\n")
    monkeypatch.setattr(swarm_cli, "_source_launch_target", lambda _name: (script, "test source"))
    monkeypatch.setattr(swarm_cli.paths, "get_user_bin_dir", lambda: tmp_path / "bin")
    result = CliRunner().invoke(swarm_cli.app, ["launch", "broken", "--message", "hello"])
    assert result.exit_code == 7


def test_operator_checkout_is_exclusive_between_processes(tmp_path, monkeypatch):
    from swarm.core import operator_plane as plane
    monkeypatch.setenv("SWARM_OPERATOR_PLANE_PATH", str(tmp_path / "plane.json"))
    plane.checkout_task("job", "parent")
    code = '''
from swarm.core.operator_plane import checkout_task, TaskBusy
try:
    checkout_task("job", "child")
except TaskBusy:
    raise SystemExit(23)
'''
    child = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=20)
    assert child.returncode == 23
    plane.release_task("job", "parent")
    # Failed claims and exceptions must release the OS file lock too.
    assert plane.checkout_task("job", "next")["worker_id"] == "next"


def test_inventory_tool_reorders_only_shortages():
    from swarm.blueprints.inventory_demo.blueprint_inventory_demo import stock_report
    result = stock_report()
    assert result == {"fictional_data": True, "orders": [
        {"sku":"notebooks", "quantity":9, "cost":36},
        {"sku":"folders", "quantity":6, "cost":18}], "total_cost":54}


def test_hermes_refreshes_running_job_with_partial_text(monkeypatch):
    from swarm.core import remotes
    from swarm.core.remote_impls import hermes
    spec = remotes.default_spec("hermes")
    calls = []
    def get(*_args, **kwargs):
        calls.append(kwargs["timeout"])
        return remotes.HttpResult(status=200, body={"id":"audit-run", "status":"completed", "output":"42"})
    monkeypatch.setattr(remotes, "http_json", get)
    text, error, job = hermes._hermes_poll_run(
        spec, run_id="audit-run", timeout=2,
        seed={"id":"audit-run", "status":"running", "output":"partial"})
    assert text == "42"
    assert not error
    assert job["status"] == "completed"
    assert len(calls) == 1
    assert 0 < calls[0] <= 2


def test_hermes_expired_budget_does_not_start_http_poll(monkeypatch):
    from swarm.core import remotes
    from swarm.core.remote_impls import hermes
    def unexpected(*_args, **_kwargs):
        pytest.fail("Expired Hermes budget made another HTTP call")
    monkeypatch.setattr(remotes, "http_json", unexpected)
    _, error, _ = hermes._hermes_poll_run(remotes.default_spec("hermes"), run_id="audit-run", timeout=0)
    assert error == "Hermes run timed out"


def test_release_metadata_and_renamed_repository_are_consistent():
    import tomllib
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    lock = tomllib.loads((root / "uv.lock").read_text())
    locked = next(p for p in lock["package"] if p["name"] == project["name"])
    assert locked["version"] == project["version"]
    assert project["version"] != "0.5.4"
    alias = tomllib.loads((root / "packaging/open-swarm-alias/pyproject.toml").read_text())["project"]
    assert alias["version"] == project["version"]
    assert f"os-core>={project['version']},<0.7" in alias["dependencies"]
    workflow = yaml.safe_load((root / ".github/workflows/publish.yml").read_text())
    for job in workflow["jobs"].values():
        assert "matthewhand/operating-swarm" in job["if"]
        assert "matthewhand/open-swarm'" not in job["if"]
    assert any(step["name"] == "Verify release tag matches package version"
               for step in workflow["jobs"]["build"]["steps"])


@pytest.mark.parametrize("suffix", ["js", "exe"])
def test_windows_npm_shim_resolves_without_a_shell(tmp_path, suffix):
    from swarm.utils.cli_path import npm_shim_argv
    target = tmp_path / "node_modules" / "example" / f"main.{suffix}"
    target.parent.mkdir(parents=True)
    target.write_text("fixture")
    (tmp_path / "node.exe").write_text("fixture")
    (tmp_path / "agent.cmd").write_text(
        'SET dp0=%~dp0\nCALL :find_dp0\n"%dp0%\\node_modules\\example\\main.' + suffix + '" %*\n')
    command = npm_shim_argv(str(tmp_path / "agent"))
    assert command[-1] == str(target.resolve())
    assert len(command) == (2 if suffix == "js" else 1)
    assert not any("cmd.exe" in part for part in command)


def test_windows_npm_shim_refuses_target_escape(tmp_path):
    from swarm.utils.cli_path import npm_shim_argv
    (tmp_path / "outside.exe").write_text("fixture")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "agent.cmd").write_text(
        'SET dp0=%~dp0\nCALL :find_dp0\n"%dp0%\\node_modules\\..\\outside.exe" %*\n')
    assert npm_shim_argv(str(tmp_path / "agent")) is None


def test_windows_npm_shim_leaves_custom_scripts_uninterpreted(tmp_path):
    from swarm.utils.cli_path import npm_shim_argv
    (tmp_path / "custom.cmd").write_text('echo "untrusted"\n')
    assert npm_shim_argv(str(tmp_path / "custom.cmd")) is None


def test_windows_native_sibling_wins_over_posix_shim(tmp_path):
    from swarm.utils.cli_path import npm_shim_argv
    (tmp_path / "agent").write_text("#!/bin/sh\n")
    native = tmp_path / "agent.exe"
    native.write_text("fixture")
    assert npm_shim_argv(str(tmp_path / "agent")) == [str(native)]


def test_cli_allowlist_keeps_windows_runtime_but_not_unrelated_secrets(monkeypatch):
    from swarm.core.cli_adapter import CliAdapter
    monkeypatch.setenv("SYSTEMROOT", "C:\\Windows")
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\fixture")
    monkeypatch.setenv("UNRELATED_API_KEY", "private-test-credential")
    adapter = CliAdapter.from_config("fixture", {"cmd":["fixture", "{prompt}"], "env_allowlist":[]})
    env = adapter._build_env("hi", ".", None)
    assert env["SYSTEMROOT"] == "C:\\Windows"
    assert env["USERPROFILE"] == "C:\\Users\\fixture"
    assert "UNRELATED_API_KEY" not in env
