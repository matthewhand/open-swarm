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

    def test_runpy_fails(self):
        """runpy.run_path executes arbitrary files — same class as importlib."""
        with pytest.raises(ValueError, match=r"runpy"):
            assert_safe_blueprint_source("import runpy\nrunpy.run_path('/tmp/evil.py')\n")

    def test_from_runpy_import_fails(self):
        with pytest.raises(ValueError, match=r"runpy"):
            assert_safe_blueprint_source("from runpy import run_module\n")

    @pytest.mark.parametrize(
        "src,match",
        [
            ("import urllib\n", r"urllib"),
            ("import urllib.request\n", r"urllib"),
            ("from urllib.request import urlopen\n", r"urllib"),
            ("import http\n", r"http"),
            ("import http.client\n", r"http"),
            ("from http.client import HTTPConnection\n", r"http"),
            ("import httpx\n", r"httpx"),
            ("from httpx import Client\n", r"httpx"),
            ("import requests\n", r"requests"),
            ("from requests import get\n", r"requests"),
            ("import aiohttp\n", r"aiohttp"),
            ("from aiohttp import ClientSession\n", r"aiohttp"),
            ("import urllib3\n", r"urllib3"),
            ("import websockets\n", r"websockets"),
            ("import ftplib\n", r"ftplib"),
            ("import smtplib\n", r"smtplib"),
        ],
    )
    def test_http_network_client_imports_fail(self, src, match):
        with pytest.raises(ValueError, match=match):
            assert_safe_blueprint_source(src)

    def test_dunder_import_fails(self):
        with pytest.raises(ValueError, match=r"__import__"):
            assert_safe_blueprint_source("__import__('os')\n")

    def test_open_write_mode_fails(self):
        with pytest.raises(ValueError, match=r"open"):
            assert_safe_blueprint_source("open('/tmp/x', 'w')\n")

    def test_open_read_mode_ok(self):
        assert_safe_blueprint_source("f = open('/tmp/x', 'r')\n")

    @pytest.mark.parametrize(
        "src",
        [
            "from pathlib import Path\nPath('/tmp/x').open('w')\n",
            "from pathlib import Path\nPath('/tmp/x').open('wb')\n",
            "from pathlib import Path\nPath('/tmp/x').open('a')\n",
            "from pathlib import Path\nPath('/tmp/x').open('x')\n",
            "from pathlib import Path\np = Path('/tmp/x')\np.open('w')\n",
            "from pathlib import Path\nPath('/tmp/x').open(mode='w')\n",
            "from pathlib import Path\nPath('/tmp/x').open('w').write('evil')\n",
        ],
    )
    def test_path_open_write_mode_fails(self, src):
        """Path.open(mode) puts mode in args[0]; must not bypass builtin open ban."""
        with pytest.raises(ValueError, match=r"open.*write mode"):
            assert_safe_blueprint_source(src)

    def test_path_open_read_mode_ok(self):
        assert_safe_blueprint_source(
            "from pathlib import Path\nf = Path('/tmp/x').open('r')\n"
        )
        assert_safe_blueprint_source(
            "from pathlib import Path\nf = Path('/tmp/x').open()\n"
        )

    def test_os_system_fails(self):
        with pytest.raises(ValueError, match=r"os\.system"):
            assert_safe_blueprint_source("import os\nos.system('id')\n")

    def test_getattr_os_system_fails(self):
        """getattr(os, \"system\") must not bypass the os.system Attribute ban."""
        with pytest.raises(ValueError, match=r"getattr\(os, 'system'\)"):
            assert_safe_blueprint_source(
                "import os\ngetattr(os, 'system')('id')\n"
            )

    def test_getattr_os_open_fails(self):
        with pytest.raises(ValueError, match=r"getattr\(os, 'open'\)"):
            assert_safe_blueprint_source(
                "import os\ngetattr(os, 'open')('/tmp/x', os.O_WRONLY)\n"
            )

    def test_getattr_asyncio_create_subprocess_fails(self):
        with pytest.raises(ValueError, match=r"getattr\(asyncio,"):
            assert_safe_blueprint_source(
                "import asyncio\ngetattr(asyncio, 'create_subprocess_exec')('id')\n"
            )

    def test_getattr_benign_still_ok(self):
        """Non-banned getattr(os, …) and ordinary getattr remain allowed."""
        assert_safe_blueprint_source(
            "import os\npath = getattr(os, 'environ', {})\n"
            "result = object()\ncontent = getattr(result, 'final_output', '')\n"
        )

    def test_os_remove_fails(self):
        with pytest.raises(ValueError, match=r"os\.remove"):
            assert_safe_blueprint_source("import os\nos.remove('/tmp/x')\n")

    def test_os_unlink_fails(self):
        with pytest.raises(ValueError, match=r"os\.unlink"):
            assert_safe_blueprint_source("import os\nos.unlink('/tmp/x')\n")

    def test_os_rename_fails(self):
        with pytest.raises(ValueError, match=r"os\.rename"):
            assert_safe_blueprint_source("import os\nos.rename('/tmp/a', '/tmp/b')\n")

    def test_from_os_import_remove_fails(self):
        with pytest.raises(ValueError, match=r"os\.remove"):
            assert_safe_blueprint_source("from os import remove\n")

    def test_os_open_fails(self):
        """os.open bypasses builtin open() write-mode ban — reject entirely."""
        with pytest.raises(ValueError, match=r"os\.open"):
            assert_safe_blueprint_source(
                "import os\nfd = os.open('/tmp/x', os.O_WRONLY | os.O_CREAT)\n"
            )

    def test_os_write_fails(self):
        with pytest.raises(ValueError, match=r"os\.write"):
            assert_safe_blueprint_source("import os\nos.write(1, b'x')\n")

    def test_from_os_import_open_fails(self):
        with pytest.raises(ValueError, match=r"os\.open"):
            assert_safe_blueprint_source("from os import open\n")

    def test_from_os_import_write_fails(self):
        with pytest.raises(ValueError, match=r"os\.write"):
            assert_safe_blueprint_source("from os import write\n")

    @pytest.mark.parametrize(
        "src,match",
        [
            (
                "import asyncio\nasyncio.create_subprocess_exec('id')\n",
                r"create_subprocess_exec",
            ),
            (
                "import asyncio\nasyncio.create_subprocess_shell('id')\n",
                r"create_subprocess_shell",
            ),
            (
                "import asyncio\nasyncio.open_connection('127.0.0.1', 80)\n",
                r"open_connection",
            ),
            (
                "import asyncio\nasyncio.open_unix_connection('/tmp/s')\n",
                r"open_unix_connection",
            ),
            (
                "import asyncio\nasyncio.start_server(lambda: None, '127.0.0.1', 0)\n",
                r"start_server",
            ),
            (
                "import asyncio\nasyncio.create_connection(lambda: None, '127.0.0.1', 80)\n",
                r"asyncio\.create_connection",
            ),
            (
                "from asyncio import create_subprocess_exec\n",
                r"asyncio\.create_subprocess_exec",
            ),
            (
                "from asyncio import open_connection\n",
                r"asyncio\.open_connection",
            ),
            (
                "loop = object()\nloop.subprocess_exec(None, 'id')\n",
                r"subprocess_exec",
            ),
        ],
    )
    def test_asyncio_process_network_escapes_fail(self, src, match):
        with pytest.raises(ValueError, match=match):
            assert_safe_blueprint_source(src)

    def test_asyncio_sleep_and_run_still_ok(self):
        src = """
import asyncio
async def main():
    await asyncio.sleep(0)
asyncio.run(main())
"""
        assert_safe_blueprint_source(src)

    def test_path_write_text_fails(self):
        with pytest.raises(ValueError, match=r"write_text"):
            assert_safe_blueprint_source(
                "from pathlib import Path\nPath('/tmp/x').write_text('evil')\n"
            )

    def test_path_unlink_fails(self):
        with pytest.raises(ValueError, match=r"unlink"):
            assert_safe_blueprint_source(
                "from pathlib import Path\np = Path('/tmp/x')\np.unlink()\n"
            )

    def test_path_write_bytes_fails(self):
        with pytest.raises(ValueError, match=r"write_bytes"):
            assert_safe_blueprint_source(
                "from pathlib import Path\nPath('/tmp/x').write_bytes(b'x')\n"
            )

    def test_path_ctor_rename_fails(self):
        with pytest.raises(ValueError, match=r"Path\.rename"):
            assert_safe_blueprint_source(
                "from pathlib import Path\nPath('/tmp/a').rename('/tmp/b')\n"
            )

    def test_path_read_only_ok(self):
        """Path import and read-only methods remain allowed."""
        src = """
from pathlib import Path
p = Path('/tmp/x')
text = p.read_text()
exists = p.exists()
parent = p.parent
name = p.name
"""
        assert_safe_blueprint_source(src)

    def test_str_replace_still_ok(self):
        assert_safe_blueprint_source("s = 'ab'.replace('a', 'c')\n")

    def test_builtins_name_fails(self):
        with pytest.raises(ValueError, match=r"__builtins__"):
            assert_safe_blueprint_source("getattr(__builtins__, 'eval')\n")

    def test_getattr_constant_attr_allowed(self):
        # Common pattern in generated team blueprints.
        assert_safe_blueprint_source(
            "result = object()\ncontent = getattr(result, 'final_output', str(result))\n"
        )

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
