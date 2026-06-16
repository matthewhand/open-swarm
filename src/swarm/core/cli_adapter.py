"""CLI agent adapter layer.

Turns an external, interactive agentic CLI (``claude``, ``gemini``, ``codex``,
``opencode`` ...) into a one-shot, awaitable subagent that takes a prompt and
returns text. This is the building block the CLI-fusion blueprints compose:
each panelist is a :class:`CliAdapter` driven entirely by configuration.

Design notes
------------
* **No shell.** The command is an argv list executed directly
  (``asyncio.create_subprocess_exec``); the prompt is passed as a discrete
  argument or on stdin, so there is no shell-injection surface.
* **Lifecycle.** Every launch runs in its own process *session*
  (``start_new_session=True``) so a hung or runaway agent — and any children it
  spawned — can be killed as a group on timeout.
* **Config-driven.** Adapters are described as plain dicts (see
  :meth:`CliAdapter.from_config`) so adding a new CLI is a config edit, not code.
"""

from __future__ import annotations

import asyncio
import codecs
import json
import logging
import os
import shutil
import signal
import time
from dataclasses import dataclass, field, replace
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

# Sentinel substituted in argv / cwd / env templates.
PROMPT_TOKEN = "{prompt}"
WORKDIR_TOKEN = "{workdir}"

DEFAULT_TIMEOUT = 180.0
# Grace period between SIGTERM and SIGKILL when reaping a timed-out agent.
TERM_GRACE = 5.0
# Auth probes should be quick; cap them well under a normal run timeout.
AUTH_TIMEOUT = 30.0

# Authentication states reported by discovery.
AUTH_AUTHENTICATED = "authenticated"
AUTH_UNAUTHENTICATED = "unauthenticated"
AUTH_UNKNOWN = "unknown"  # no auth_check configured, or the probe was inconclusive
AUTH_NOT_INSTALLED = "not_installed"

# Smoke-probe states: does the configured cmd actually *return* in print mode?
SMOKE_OK = "ok"                          # produced output and exited 0 in time
SMOKE_HANG = "hang"                      # timed out — almost always a wrong/missing
                                         # non-interactive flag (the CLI waited on input)
SMOKE_ERROR = "error"                    # ran but exited non-zero or produced nothing
SMOKE_NOT_INSTALLED = "not_installed"

# A trivial prompt for the smoke probe; cheap, but DOES invoke the model once.
DEFAULT_SMOKE_PROMPT = "Reply with the single word: OK"
# Smoke probes should be quick; cap well under a normal run.
SMOKE_TIMEOUT = 60.0


class CliAdapterError(Exception):
    """Raised for configuration/lookup problems (not runtime CLI failures)."""


@dataclass(frozen=True)
class CliAgentConfig:
    """Declarative description of how to run one agentic CLI one-shot.

    Attributes
    ----------
    name:
        Logical adapter name (e.g. ``"claude"``).
    cmd:
        argv list. Use ``{prompt}`` where the prompt should be injected and
        ``{workdir}`` for the working directory. When ``prompt_mode == "stdin"``
        the ``{prompt}`` token is optional and the prompt is written to stdin.
    prompt_mode:
        ``"arg"`` (default) substitutes ``{prompt}`` into ``cmd``; ``"stdin"``
        feeds the prompt to the process's standard input.
    parse:
        ``"text"`` returns trimmed stdout. ``"json:<dotpath>"`` parses stdout as
        JSON and extracts the value at the dotted path (e.g. ``json:.result`` or
        ``json:.choices.0.message.content``). On parse failure the raw stdout is
        returned and ``CliResult.parse_error`` is set.
    cwd:
        Working directory template (``{workdir}`` allowed). When None, the
        per-call ``workdir`` is used, else the current directory.
    env:
        Extra environment variables (values may contain ``{prompt}``/``{workdir}``).
        Merged onto the parent environment.
    env_allowlist:
        When None (default), the child inherits the full parent environment —
        convenient, but every panelist then sees every API key. When set to a
        list of names, the child gets only those vars (plus a small essential
        set like ``PATH``/``HOME``) from the parent, isolating each CLI's
        secrets. ``env`` is always applied on top.
    timeout:
        Seconds before the agent (and its process group) is killed.
    mode:
        Informational label describing the safety posture (e.g. ``"readonly"``,
        ``"write"``). Not enforced here — it documents intent and is surfaced in
        results/logs.
    """

    name: str
    cmd: list[str]
    prompt_mode: str = "arg"
    parse: str = "text"
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    env_allowlist: list[str] | None = None
    timeout: float = DEFAULT_TIMEOUT
    mode: str = "default"
    auth_check: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.cmd:
            raise CliAdapterError(f"CLI adapter '{self.name}' has an empty cmd")
        if self.prompt_mode not in ("arg", "stdin"):
            raise CliAdapterError(
                f"CLI adapter '{self.name}': prompt_mode must be 'arg' or 'stdin', "
                f"got {self.prompt_mode!r}"
            )
        if self.prompt_mode == "arg" and not any(PROMPT_TOKEN in part for part in self.cmd):
            raise CliAdapterError(
                f"CLI adapter '{self.name}': prompt_mode 'arg' requires a "
                f"'{PROMPT_TOKEN}' token somewhere in cmd"
            )
        if self.auth_check is not None and (
            not isinstance(self.auth_check, list)
            or not all(isinstance(p, str) for p in self.auth_check)
            or not self.auth_check
        ):
            raise CliAdapterError(
                f"CLI adapter '{self.name}': auth_check must be a non-empty list of strings"
            )


@dataclass
class CliResult:
    """Outcome of a single CLI agent invocation."""

    name: str
    ok: bool
    text: str
    returncode: int | None = None
    duration: float = 0.0
    timed_out: bool = False
    parse_error: str | None = None
    error: str | None = None
    stderr: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "text": self.text,
            "returncode": self.returncode,
            "duration": round(self.duration, 3),
            "timed_out": self.timed_out,
            "parse_error": self.parse_error,
            "error": self.error,
            "stderr": self.stderr,
        }


@dataclass
class SmokeResult:
    """Outcome of a non-interactive smoke probe (see :meth:`CliAdapter.smoke_check`)."""

    name: str
    status: str
    detail: str = ""
    duration: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == SMOKE_OK

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "duration": round(self.duration, 3),
        }


@dataclass
class CliStreamChunk:
    """One event from :meth:`CliAdapter.stream_run`.

    Either an incremental output delta (``delta`` set, ``final=False``) or the
    terminal event (``final=True``) carrying the assembled :class:`CliResult`.
    """

    delta: str = ""
    final: bool = False
    result: CliResult | None = None


def _apply_tokens(value: str, prompt: str, workdir: str) -> str:
    return value.replace(PROMPT_TOKEN, prompt).replace(WORKDIR_TOKEN, workdir)


def _extract_json_path(data: Any, dotpath: str) -> Any:
    """Navigate a dotted path into parsed JSON. Supports list indices.

    ``.result`` -> data["result"]; ``.choices.0.message.content`` walks the list.
    Leading dot optional. Raises KeyError/IndexError/TypeError on a bad path.
    """
    cur = data
    for key in dotpath.strip(".").split("."):
        if key == "":
            continue
        if isinstance(cur, list):
            cur = cur[int(key)]
        else:
            cur = cur[key]
    return cur


class CliAdapter:
    """Runs one configured agentic CLI as an awaitable one-shot subagent."""

    def __init__(self, config: CliAgentConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @classmethod
    def from_config(cls, name: str, raw: dict[str, Any]) -> CliAdapter:
        """Build an adapter from a config dict (see :class:`CliAgentConfig`)."""
        if not isinstance(raw, dict):
            raise CliAdapterError(f"CLI adapter '{name}' config must be a dict")
        cmd = raw.get("cmd")
        if not isinstance(cmd, list) or not all(isinstance(p, str) for p in cmd):
            raise CliAdapterError(f"CLI adapter '{name}': 'cmd' must be a list of strings")
        cfg = CliAgentConfig(
            name=name,
            cmd=list(cmd),
            prompt_mode=raw.get("prompt_mode", "arg"),
            parse=raw.get("parse", "text"),
            cwd=raw.get("cwd"),
            env=dict(raw.get("env", {})),
            env_allowlist=raw.get("env_allowlist"),
            timeout=float(raw.get("timeout", DEFAULT_TIMEOUT)),
            mode=raw.get("mode", "default"),
            auth_check=raw.get("auth_check"),
        )
        return cls(cfg)

    def is_available(self) -> bool:
        """True when the CLI executable is resolvable on PATH (or absolute)."""
        exe = self.config.cmd[0]
        if os.path.sep in exe:
            return os.path.isfile(exe) and os.access(exe, os.X_OK)
        return shutil.which(exe) is not None

    def _build_invocation(
        self, prompt: str, workdir: str
    ) -> tuple[list[str], bytes | None]:
        """Return (argv, stdin_bytes) for the given prompt."""
        argv = [_apply_tokens(part, prompt, workdir) for part in self.config.cmd]
        stdin_bytes: bytes | None = None
        if self.config.prompt_mode == "stdin":
            stdin_bytes = prompt.encode("utf-8")
        return argv, stdin_bytes

    def _parse_output(self, stdout: str) -> tuple[str, str | None]:
        """Return (text, parse_error). parse_error is None on success."""
        spec = self.config.parse or "text"
        if spec == "text":
            return stdout.strip(), None
        if spec.startswith("json"):
            dotpath = spec[len("json"):].lstrip(":")
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as exc:
                return stdout.strip(), f"invalid JSON: {exc}"
            if not dotpath:
                return (
                    data if isinstance(data, str) else json.dumps(data),
                    None,
                )
            try:
                value = _extract_json_path(data, dotpath)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                return stdout.strip(), f"json path '{dotpath}' not found: {exc}"
            return (value if isinstance(value, str) else json.dumps(value)), None
        return stdout.strip(), f"unknown parse spec {spec!r}"

    async def run(
        self,
        prompt: str,
        *,
        workdir: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> CliResult:
        """Launch the CLI, await its answer, and parse the result.

        Never raises for runtime failures — a non-zero exit, timeout, or missing
        executable comes back as a :class:`CliResult` with ``ok=False``.
        """
        cfg = self.config
        effective_workdir = (
            _apply_tokens(cfg.cwd, prompt, workdir or os.getcwd())
            if cfg.cwd
            else (workdir or os.getcwd())
        )
        argv, stdin_bytes = self._build_invocation(prompt, effective_workdir)

        env = self._build_env(prompt, effective_workdir, extra_env)

        if not self.is_available():
            return CliResult(
                name=cfg.name,
                ok=False,
                text="",
                error=f"executable not found on PATH: {cfg.cmd[0]!r}",
            )

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if stdin_bytes is not None else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=effective_workdir,
                env=env,
                start_new_session=True,  # own process group, so we can kill the tree
            )
        except (OSError, ValueError) as exc:
            return CliResult(
                name=cfg.name, ok=False, text="",
                error=f"failed to launch: {exc}", duration=time.monotonic() - start,
            )

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes), timeout=cfg.timeout
            )
        except asyncio.TimeoutError:
            timed_out = True
            await self._terminate(proc)
            stdout_b, stderr_b = b"", b""
        duration = time.monotonic() - start

        stdout = (stdout_b or b"").decode("utf-8", errors="replace")
        stderr = (stderr_b or b"").decode("utf-8", errors="replace")

        if timed_out:
            return CliResult(
                name=cfg.name, ok=False, text=stdout.strip(), returncode=proc.returncode,
                duration=duration, timed_out=True, stderr=stderr.strip(),
                error=f"timed out after {cfg.timeout}s",
            )

        if proc.returncode != 0:
            return CliResult(
                name=cfg.name, ok=False, text=stdout.strip(), returncode=proc.returncode,
                duration=duration, stderr=stderr.strip(),
                error=f"exited {proc.returncode}: {stderr.strip()[:500]}",
            )

        text, parse_error = self._parse_output(stdout)
        return CliResult(
            name=cfg.name, ok=True, text=text, returncode=0, duration=duration,
            parse_error=parse_error, stderr=stderr.strip(),
        )

    async def stream_run(
        self,
        prompt: str,
        *,
        workdir: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> AsyncIterator[CliStreamChunk]:
        """Like :meth:`run`, but yield stdout incrementally as it arrives.

        Yields :class:`CliStreamChunk` deltas while the CLI produces output, then
        a single terminal chunk (``final=True``) carrying the full
        :class:`CliResult`. The terminal result's ``text`` is parsed per the
        adapter's ``parse`` spec; for ``json:`` adapters the deltas are raw stdout
        (the parsed value only exists once the whole document is read), so callers
        that need clean incremental text should stream only ``parse="text"``
        adapters. Never raises for runtime failures.
        """
        cfg = self.config
        effective_workdir = (
            _apply_tokens(cfg.cwd, prompt, workdir or os.getcwd())
            if cfg.cwd
            else (workdir or os.getcwd())
        )
        argv, stdin_bytes = self._build_invocation(prompt, effective_workdir)
        env = self._build_env(prompt, effective_workdir, extra_env)

        if not self.is_available():
            yield CliStreamChunk(
                final=True,
                result=CliResult(
                    name=cfg.name, ok=False, text="",
                    error=f"executable not found on PATH: {cfg.cmd[0]!r}",
                ),
            )
            return

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if stdin_bytes is not None else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=effective_workdir,
                env=env,
                start_new_session=True,
            )
        except (OSError, ValueError) as exc:
            yield CliStreamChunk(
                final=True,
                result=CliResult(
                    name=cfg.name, ok=False, text="",
                    error=f"failed to launch: {exc}", duration=time.monotonic() - start,
                ),
            )
            return

        if stdin_bytes is not None and proc.stdin is not None:
            try:
                proc.stdin.write(stdin_bytes)
                await proc.stdin.drain()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass

        # Drain stderr concurrently so its pipe can never fill and deadlock the
        # process while we are only reading stdout.
        stderr_buf: list[bytes] = []

        async def _drain_stderr() -> None:
            assert proc.stderr is not None
            try:
                while True:
                    blob = await proc.stderr.read(4096)
                    if not blob:
                        break
                    stderr_buf.append(blob)
            except (asyncio.CancelledError, OSError):
                pass

        stderr_task = asyncio.ensure_future(_drain_stderr())

        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        out_parts: list[str] = []
        timed_out = False
        deadline = start + cfg.timeout
        assert proc.stdout is not None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                blob = await asyncio.wait_for(proc.stdout.read(4096), timeout=remaining)
            except asyncio.TimeoutError:
                timed_out = True
                break
            if not blob:  # EOF
                break
            text = decoder.decode(blob)
            if text:
                out_parts.append(text)
                yield CliStreamChunk(delta=text)

        tail = decoder.decode(b"", final=True)
        if tail:
            out_parts.append(tail)
            yield CliStreamChunk(delta=tail)

        duration = time.monotonic() - start
        stdout = "".join(out_parts)

        if timed_out:
            await self._terminate(proc)
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass
            stderr = b"".join(stderr_buf).decode("utf-8", errors="replace")
            yield CliStreamChunk(
                final=True,
                result=CliResult(
                    name=cfg.name, ok=False, text=stdout.strip(), returncode=proc.returncode,
                    duration=duration, timed_out=True, stderr=stderr.strip(),
                    error=f"timed out after {cfg.timeout}s",
                ),
            )
            return

        await proc.wait()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass
        stderr = b"".join(stderr_buf).decode("utf-8", errors="replace")

        if proc.returncode != 0:
            yield CliStreamChunk(
                final=True,
                result=CliResult(
                    name=cfg.name, ok=False, text=stdout.strip(), returncode=proc.returncode,
                    duration=duration, stderr=stderr.strip(),
                    error=f"exited {proc.returncode}: {stderr.strip()[:500]}",
                ),
            )
            return

        text, parse_error = self._parse_output(stdout)
        yield CliStreamChunk(
            final=True,
            result=CliResult(
                name=cfg.name, ok=True, text=text, returncode=0, duration=duration,
                parse_error=parse_error, stderr=stderr.strip(),
            ),
        )

    # Always-passed vars so a locked-down CLI can still run and resolve itself.
    _ESSENTIAL_ENV = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM")

    def _build_env(
        self, prompt: str, workdir: str, extra_env: dict[str, str] | None
    ) -> dict[str, str]:
        cfg = self.config
        if cfg.env_allowlist is None:
            env = os.environ.copy()
        else:
            keep = (*self._ESSENTIAL_ENV, *cfg.env_allowlist)
            env = {k: os.environ[k] for k in keep if k in os.environ}
        for key, val in cfg.env.items():
            env[key] = _apply_tokens(val, prompt, workdir)
        if extra_env:
            env.update(extra_env)
        return env

    async def check_auth(self) -> str:
        """Probe whether this CLI is authenticated.

        Returns one of AUTH_NOT_INSTALLED (executable missing), AUTH_UNKNOWN
        (no ``auth_check`` configured, or the probe errored/timed out),
        AUTH_AUTHENTICATED (``auth_check`` exited 0), or AUTH_UNAUTHENTICATED.
        Never raises.
        """
        cfg = self.config
        if not self.is_available():
            return AUTH_NOT_INSTALLED
        if not cfg.auth_check:
            return AUTH_UNKNOWN
        workdir = os.getcwd()
        argv = [_apply_tokens(p, "", workdir) for p in cfg.auth_check]
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._build_env("", workdir, None),
                start_new_session=True,
            )
        except (OSError, ValueError):
            return AUTH_UNKNOWN
        try:
            await asyncio.wait_for(proc.communicate(), timeout=min(cfg.timeout, AUTH_TIMEOUT))
        except asyncio.TimeoutError:
            await self._terminate(proc)
            return AUTH_UNKNOWN
        return AUTH_AUTHENTICATED if proc.returncode == 0 else AUTH_UNAUTHENTICATED

    async def smoke_check(
        self, *, prompt: str = DEFAULT_SMOKE_PROMPT, timeout: float | None = None
    ) -> SmokeResult:
        """Run one trivial one-shot to confirm the cmd *returns* in print mode.

        Unlike :meth:`check_auth` (a cheap exit-code probe), this actually
        invokes the CLI — and therefore the model — once, so it consumes a small
        amount of quota. It exists to catch the most common misconfiguration: a
        missing/wrong non-interactive flag, which makes the CLI block on input
        and hang until the timeout. Returns a :class:`SmokeResult`; never raises.
        """
        if not self.is_available():
            return SmokeResult(self.name, SMOKE_NOT_INSTALLED)
        t = timeout if timeout is not None else min(self.config.timeout, SMOKE_TIMEOUT)
        probe = CliAdapter(replace(self.config, timeout=t))
        res = await probe.run(prompt)
        if res.timed_out:
            return SmokeResult(
                self.name, SMOKE_HANG,
                "no output before timeout — check the non-interactive flag",
                res.duration,
            )
        if not res.ok:
            return SmokeResult(self.name, SMOKE_ERROR, (res.error or "")[:200], res.duration)
        if not (res.text or "").strip():
            return SmokeResult(self.name, SMOKE_ERROR, "exited 0 but produced no output", res.duration)
        return SmokeResult(self.name, SMOKE_OK, "", res.duration)

    @staticmethod
    async def _terminate(proc: asyncio.subprocess.Process) -> None:
        """Kill a timed-out process group: SIGTERM, grace, then SIGKILL."""
        if proc.returncode is not None:
            return
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                return
            try:
                await asyncio.wait_for(proc.wait(), timeout=TERM_GRACE)
                return
            except asyncio.TimeoutError:
                continue


@dataclass
class CliDiscovery:
    """Autodiscovery status for one configured CLI adapter."""

    name: str
    installed: bool
    executable: str | None
    mode: str
    authenticated: str = AUTH_UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "installed": self.installed,
            "executable": self.executable,
            "mode": self.mode,
            "authenticated": self.authenticated,
        }


class CliAdapterRegistry:
    """Holds the configured CLI adapters and resolves them by name."""

    def __init__(self, adapters: dict[str, CliAdapter] | None = None):
        self._adapters: dict[str, CliAdapter] = adapters or {}

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> CliAdapterRegistry:
        """Build a registry from the top-level swarm config's ``cli_agents`` block."""
        adapters: dict[str, CliAdapter] = {}
        raw_agents = (config or {}).get("cli_agents", {}) or {}
        for name, raw in raw_agents.items():
            try:
                adapters[name] = CliAdapter.from_config(name, raw)
            except CliAdapterError as exc:
                logger.warning("Skipping CLI adapter %r: %s", name, exc)
        return cls(adapters)

    def get(self, name: str) -> CliAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise CliAdapterError(
                f"no CLI adapter named {name!r}; configured: {sorted(self._adapters)}"
            ) from exc

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def available(self) -> list[str]:
        """Names of adapters whose executable is present on this host."""
        return sorted(n for n, a in self._adapters.items() if a.is_available())

    def discover(self) -> list[CliDiscovery]:
        """Report install status for every configured adapter (sorted by name)."""
        out: list[CliDiscovery] = []
        for name in self.names():
            cfg = self._adapters[name].config
            exe = cfg.cmd[0]
            resolved = exe if os.path.sep in exe else shutil.which(exe)
            out.append(
                CliDiscovery(
                    name=name,
                    installed=self._adapters[name].is_available(),
                    executable=resolved,
                    mode=cfg.mode,
                )
            )
        return out

    async def discover_auth(self) -> list[CliDiscovery]:
        """Like discover(), but also probe each adapter's authentication state.

        Runs every adapter's ``auth_check`` concurrently. Slower than
        :meth:`discover` (it launches subprocesses), so it is opt-in.
        """
        rows = self.discover()

        async def _fill(row: CliDiscovery) -> CliDiscovery:
            row.authenticated = await self._adapters[row.name].check_auth()
            return row

        return list(await asyncio.gather(*(_fill(r) for r in rows)))

    async def smoke_check_all(
        self, *, names: list[str] | None = None, timeout: float | None = None
    ) -> list[SmokeResult]:
        """Smoke-probe adapters concurrently (all configured, or a subset).

        Each probe runs one trivial one-shot, so this consumes a little quota per
        installed adapter — it is opt-in, not part of plain :meth:`discover`.
        """
        target = names if names is not None else self.names()
        adapters = [self._adapters[n] for n in target if n in self._adapters]
        return list(
            await asyncio.gather(*(a.smoke_check(timeout=timeout) for a in adapters))
        )

    def resolve_panel(self, names: list[str]) -> list[CliAdapter]:
        """Resolve a list of adapter names to adapters (raises on unknown)."""
        return [self.get(n) for n in names]

    def with_overrides(self, overrides: dict[str, dict[str, Any]]) -> CliAdapterRegistry:
        """Return a copy with per-adapter field overrides applied (non-mutating)."""
        merged = dict(self._adapters)
        for name, patch in (overrides or {}).items():
            base = merged.get(name)
            cfg = base.config if base else None
            if cfg is None:
                merged[name] = CliAdapter.from_config(name, patch)
            else:
                merged[name] = CliAdapter(replace(cfg, **patch))
        return CliAdapterRegistry(merged)
