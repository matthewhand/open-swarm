import os
import sys
import types
from pathlib import Path

from swarm.extensions.cli.commands import compile_blueprint


def _write_blueprint(tmp_root: Path, name: str, content: str = "print('ok')") -> Path:
    blueprint_dir = tmp_root / name
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    entry = blueprint_dir / "main.py"
    entry.write_text(content, encoding="utf-8")
    return entry


def _mock_agents_module(monkeypatch):
    mock_agents = types.ModuleType("agents")
    def set_default_openai_client(*_args, **_kwargs):
        return None

    mock_agents.set_default_openai_client = set_default_openai_client
    monkeypatch.setitem(sys.modules, "agents", mock_agents)


def _write_blueprint_with_metadata(
    tmp_root: Path,
    name: str,
    *,
    abbreviation: str | None = None,
    filename: str | None = None,
) -> Path:
    blueprint_dir = tmp_root / name
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    entry_name = filename or f"{name}.py"
    entry = blueprint_dir / entry_name
    entry.write_text(
        f"""
from swarm.core.blueprint_base import BlueprintBase


class DemoBlueprint(BlueprintBase):
    metadata = {{"name": "{name}", "abbreviation": {abbreviation!r}}}

    async def run(self, messages, **kwargs):
        raise NotImplementedError
""",
        encoding="utf-8",
    )
    return entry


def test_compile_blueprint_creates_test_mode_shim(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")

    entry = _write_blueprint(compile_blueprint.paths.get_user_blueprints_dir(), "demo")

    exe_path = compile_blueprint.compile_blueprint_executable("demo", force=True)

    content = exe_path.read_text(encoding="utf-8")
    assert entry.as_posix() in content
    assert os.access(exe_path, os.X_OK)


def test_compile_all_prefers_user_sources(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")

    user_root = compile_blueprint.paths.get_user_blueprints_dir()
    bundled_root = tmp_path / "bundled"
    bundled_blueprints = bundled_root / "blueprints"
    bundled_blueprints.mkdir(parents=True, exist_ok=True)

    user_entry = _write_blueprint(user_root, "shared", "print('user')")
    _write_blueprint(user_root, "user_only", "print('user_only')")
    _write_blueprint(bundled_blueprints, "shared", "print('bundled')")
    _write_blueprint(bundled_blueprints, "bundled_only", "print('bundled_only')")

    monkeypatch.setattr(
        compile_blueprint.pkg_resources, "files", lambda _: bundled_root
    )

    result = compile_blueprint.compile_all_available_blueprints(force=True)

    assert set(result.succeeded) == {"shared", "user_only", "bundled_only"}
    shared_content = result.succeeded["shared"].read_text(encoding="utf-8")
    assert user_entry.as_posix() in shared_content
    assert not result.failed


def test_compile_blueprint_uses_abbreviation(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    _mock_agents_module(monkeypatch)

    entry = _write_blueprint_with_metadata(
        compile_blueprint.paths.get_user_blueprints_dir(), "demo", abbreviation="dm"
    )

    exe_path = compile_blueprint.compile_blueprint_executable("demo", force=True)

    assert exe_path.name == "dm"
    content = exe_path.read_text(encoding="utf-8")
    assert entry.as_posix() in content


def test_compile_blueprint_prefers_named_entry_files(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    _mock_agents_module(monkeypatch)

    entry = _write_blueprint_with_metadata(
        compile_blueprint.paths.get_user_blueprints_dir(),
        "custom",
        filename="blueprint_custom.py",
    )

    exe_path = compile_blueprint.compile_blueprint_executable("custom", force=True)

    assert "blueprint_custom.py" in exe_path.read_text(encoding="utf-8")
    assert entry.as_posix() in exe_path.read_text(encoding="utf-8")
