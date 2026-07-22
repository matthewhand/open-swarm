"""Unit tests for the user-blueprint AST sandbox gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.core.blueprint_sandbox import (
    assert_safe_blueprint_source,
    sandbox_enabled,
)


SAFE_MINIMAL_BLUEPRINT = '''\
from __future__ import annotations

from typing import Any, AsyncGenerator

from swarm.core.blueprint_base import BlueprintBase


class SafeAgent(BlueprintBase):
    metadata = {
        "name": "safe_agent",
        "description": "minimal safe blueprint",
        "version": "0.0.1",
    }

    async def run(self, messages, stream: bool = False) -> AsyncGenerator:
        yield {"role": "assistant", "content": "ok"}
'''


class TestAssertSafeBlueprintSource:
    def test_safe_minimal_blueprint_passes(self):
        assert_safe_blueprint_source(SAFE_MINIMAL_BLUEPRINT)  # no raise

    def test_exec_call_fails(self):
        src = SAFE_MINIMAL_BLUEPRINT + "\nexec('print(1)')\n"
        with pytest.raises(ValueError, match=r"exec"):
            assert_safe_blueprint_source(src)

    def test_eval_call_fails(self):
        src = "x = eval('1+1')\n"
        with pytest.raises(ValueError, match=r"eval"):
            assert_safe_blueprint_source(src)

    def test_import_subprocess_fails(self):
        src = "import subprocess\n"
        with pytest.raises(ValueError, match=r"subprocess"):
            assert_safe_blueprint_source(src)

    def test_from_import_ctypes_fails(self):
        src = "from ctypes import CDLL\n"
        with pytest.raises(ValueError, match=r"ctypes"):
            assert_safe_blueprint_source(src)

    def test_import_pickle_fails(self):
        with pytest.raises(ValueError, match=r"pickle"):
            assert_safe_blueprint_source("import pickle\n")

    def test_importlib_fails(self):
        with pytest.raises(ValueError, match=r"importlib"):
            assert_safe_blueprint_source("import importlib\n")

    def test_dunder_import_fails(self):
        with pytest.raises(ValueError, match=r"__import__"):
            assert_safe_blueprint_source("__import__('os')\n")

    def test_open_write_mode_fails(self):
        with pytest.raises(ValueError, match=r"open"):
            assert_safe_blueprint_source("open('/tmp/x', 'w')\n")

    def test_open_read_mode_ok(self):
        assert_safe_blueprint_source("f = open('/tmp/x', 'r')\n")

    def test_os_system_fails(self):
        with pytest.raises(ValueError, match=r"os\.system"):
            assert_safe_blueprint_source("import os\nos.system('id')\n")

    def test_getattr_fails(self):
        with pytest.raises(ValueError, match=r"getattr"):
            assert_safe_blueprint_source("getattr(__builtins__, 'eval')\n")

    def test_allowed_imports_pass(self):
        src = """
import asyncio
from pathlib import Path
from typing import Any
from swarm.core.blueprint_base import BlueprintBase
"""
        assert_safe_blueprint_source(src)

    def test_syntax_error_raises_value_error(self):
        with pytest.raises(ValueError, match=r"syntax"):
            assert_safe_blueprint_source("def (\n")


class TestSandboxEnabledEnv:
    def test_default_true(self, monkeypatch):
        monkeypatch.delenv("SWARM_USER_BLUEPRINT_SANDBOX", raising=False)
        assert sandbox_enabled() is True

    def test_false_opt_out(self, monkeypatch):
        monkeypatch.setenv("SWARM_USER_BLUEPRINT_SANDBOX", "false")
        assert sandbox_enabled() is False

    def test_true_explicit(self, monkeypatch):
        monkeypatch.setenv("SWARM_USER_BLUEPRINT_SANDBOX", "1")
        assert sandbox_enabled() is True


class TestDiscoverySkipsUnsafe:
    def test_discover_skips_unsafe_user_blueprint(self, tmp_path, monkeypatch):
        """Unsafe source under a sandboxed root is skipped, not exec'd."""
        from swarm.core import blueprint_discovery as bd

        monkeypatch.setenv("SWARM_USER_BLUEPRINT_SANDBOX", "true")

        bp_dir = tmp_path / "evil_bp"
        bp_dir.mkdir()
        (bp_dir / "evil_bp.py").write_text(
            "import subprocess\n"
            "from swarm.core.blueprint_base import BlueprintBase\n"
            "class Evil(BlueprintBase):\n"
            "    metadata = {'name': 'evil_bp'}\n"
            "    async def run(self, messages, **kw):\n"
            "        yield {}\n",
            encoding="utf-8",
        )

        found = bd.discover_blueprints(str(tmp_path), sandboxed=True)
        assert "evil_bp" not in found
        assert found == {}

    def test_discover_loads_safe_when_sandboxed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SWARM_USER_BLUEPRINT_SANDBOX", "true")
        from swarm.core import blueprint_discovery as bd

        bp_dir = tmp_path / "safe_bp"
        bp_dir.mkdir()
        (bp_dir / "safe_bp.py").write_text(SAFE_MINIMAL_BLUEPRINT, encoding="utf-8")

        found = bd.discover_blueprints(str(tmp_path), sandboxed=True)
        assert "safe_bp" in found
        assert found["safe_bp"]["metadata"].get("name") in ("safe_agent", "safe_bp")

    def test_sandbox_opt_out_loads_banned_import(self, tmp_path, monkeypatch):
        """With SWARM_USER_BLUEPRINT_SANDBOX=false, AST gate is skipped.

        The module still must be valid Python that imports successfully; we
        use a banned-import module that does not call the import at class
        body in a failing way — import subprocess succeeds if the package
        exists.  We only assert the sandbox does not *skip* the file.
        """
        monkeypatch.setenv("SWARM_USER_BLUEPRINT_SANDBOX", "false")
        from swarm.core import blueprint_discovery as bd

        bp_dir = tmp_path / "sub_bp"
        bp_dir.mkdir()
        (bp_dir / "sub_bp.py").write_text(
            "import subprocess  # would be banned when sandbox on\n"
            "from swarm.core.blueprint_base import BlueprintBase\n"
            "class SubBP(BlueprintBase):\n"
            "    metadata = {'name': 'sub_bp'}\n"
            "    async def run(self, messages, **kw):\n"
            "        if False:\n"
            "            yield {}\n",
            encoding="utf-8",
        )

        found = bd.discover_blueprints(str(tmp_path), sandboxed=True)
        # sandboxed=True is overridden by env opt-out via sandbox_enabled()
        assert "sub_bp" in found
