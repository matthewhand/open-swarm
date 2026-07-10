"""Participant backends for MoA: fake (CI), grok (live consensus), acpx (optional).

Codex is **not** required. Preferred live path is local ``grok -p`` via
:class:`GrokParticipantBackend`. acpx remains available for multi-vendor CLIs
when those agents are installed and authenticated.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from swarm.core.moa.policy import (
    DEFAULT_PARTICIPANT_PERMISSION,
    WriteDeniedError,
    assert_participant_permission,
)
from swarm.core.moa.types import ParticipantOpinion, PermissionMode

logger = logging.getLogger(__name__)

READ_ONLY_PARTICIPANT_PREAMBLE = (
    "You are a read-only consultant in a Mixture of Agents panel. "
    "Inspect and reason only. Propose patches as text or unified diffs. "
    "Do not modify files, run destructive commands, commit, install packages, "
    "or change system state.\n\n"
)


@runtime_checkable
class ParticipantBackend(Protocol):
    """Consult one named participant agent; always under read-only policy."""

    async def consult(
        self,
        agent: str,
        prompt: str,
        *,
        cwd: str | None = None,
        permission: str = DEFAULT_PARTICIPANT_PERMISSION.value,
    ) -> ParticipantOpinion: ...


# ---------------------------------------------------------------------------
# Write surface (orchestrator-only)
# ---------------------------------------------------------------------------


@dataclass
class RecordingWriteSurface:
    """Spy filesystem used in tests to prove write isolation.

    * ``write`` — orchestrator path (allowed).
    * ``write_as_participant`` — always raises WriteDeniedError.
    """

    writes: list[tuple[str, str]] = field(default_factory=list)

    def write(self, path: str, content: str) -> None:
        self.writes.append((path, content))

    def write_as_participant(self, path: str, content: str) -> None:
        raise WriteDeniedError(
            f"MoA participants cannot write; refused write to {path!r}"
        )


# ---------------------------------------------------------------------------
# Fake backend (tests / CI)
# ---------------------------------------------------------------------------


class FakeParticipantBackend:
    """In-memory participant backend; records calls and never writes."""

    def __init__(
        self,
        responses: dict[str, str],
        *,
        write_surface: RecordingWriteSurface | None = None,
        errors: dict[str, str] | None = None,
    ) -> None:
        self.responses = dict(responses)
        self.errors = dict(errors or {})
        self.write_surface = write_surface or RecordingWriteSurface()
        self.calls: list[dict[str, Any]] = []

    async def consult(
        self,
        agent: str,
        prompt: str,
        *,
        cwd: str | None = None,
        permission: str = DEFAULT_PARTICIPANT_PERMISSION.value,
    ) -> ParticipantOpinion:
        mode = assert_participant_permission(permission)
        self.calls.append(
            {
                "agent": agent,
                "prompt": prompt,
                "cwd": cwd,
                "permission": mode,
            }
        )
        if agent in self.errors:
            return ParticipantOpinion(
                name=agent,
                text="",
                ok=False,
                permission_mode=mode,
                error=self.errors[agent],
            )
        text = self.responses.get(agent)
        if text is None:
            return ParticipantOpinion(
                name=agent,
                text="",
                ok=False,
                permission_mode=mode,
                error=f"unknown participant {agent!r}",
            )
        return ParticipantOpinion(
            name=agent,
            text=text,
            ok=True,
            permission_mode=mode,
        )


# ---------------------------------------------------------------------------
# Live consensus: local grok CLI (first-class; no Codex)
# ---------------------------------------------------------------------------


class GrokParticipantBackend:
    """Read-only MoA participant via local ``grok -p`` (xAI Grok Build CLI).

    First-class live consensus path for open-swarm. Multi-seat labels
    (``participants=["analyst","critic"]``) each spawn a separate one-shot
    ``grok -p`` with the same read-only framing. Write tools are disallowed at
    the CLI flag layer; MoA policy still treats all output as opinion only.
    """

    def __init__(self, grok_bin: str = "grok", default_timeout: float = 180.0) -> None:
        self.grok_bin = grok_bin
        self.default_timeout = default_timeout
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        if os.path.sep in self.grok_bin:
            return os.path.isfile(self.grok_bin) and os.access(self.grok_bin, os.X_OK)
        return shutil.which(self.grok_bin) is not None

    def build_command(self, prompt: str, *, cwd: str | None = None) -> list[str]:
        # --disallowed-tools aims to keep grok from editing; MoA still treats output as opinion only.
        argv = [
            self.grok_bin,
            "-p",
            prompt,
            "--disallowed-tools",
            "Write,Edit,MultiEdit,NotebookEdit",
            "--output-format",
            "plain",
            "--max-turns",
            "4",
            "--no-subagents",
            "--no-plan",
        ]
        if cwd:
            argv.extend(["--cwd", cwd])
        return argv

    async def consult(
        self,
        agent: str,
        prompt: str,
        *,
        cwd: str | None = None,
        permission: str = DEFAULT_PARTICIPANT_PERMISSION.value,
    ) -> ParticipantOpinion:
        mode = assert_participant_permission(permission)
        # Multi-seat: label is recorded; each seat is a separate one-shot.
        seat_prompt = prompt
        if agent and agent.lower() not in ("grok", "default", ""):
            seat_prompt = (
                f"[MoA seat: {agent}] Answer only from this seat's perspective.\n\n"
                f"{prompt}"
            )
        self.calls.append(
            {"agent": agent, "prompt": seat_prompt, "cwd": cwd, "permission": mode}
        )
        full = READ_ONLY_PARTICIPANT_PREAMBLE + (seat_prompt or "")
        argv = self.build_command(full, cwd=cwd)
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            return ParticipantOpinion(
                name=agent,
                text="",
                ok=False,
                permission_mode=mode,
                error=f"grok not found: {e}",
            )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.default_timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ParticipantOpinion(
                name=agent,
                text="",
                ok=False,
                permission_mode=mode,
                error=f"grok timed out after {self.default_timeout}s",
            )
        stdout = (stdout_b or b"").decode("utf-8", errors="replace").strip()
        stderr = (stderr_b or b"").decode("utf-8", errors="replace").strip()
        rc = proc.returncode if proc.returncode is not None else -1
        if rc == 0 and stdout:
            return ParticipantOpinion(
                name=agent,
                text=stdout,
                ok=True,
                permission_mode=mode,
                meta={"returncode": rc, "backend": "grok"},
            )
        return ParticipantOpinion(
            name=agent,
            text=stdout,
            ok=False,
            permission_mode=mode,
            error=stderr or stdout or f"grok exited {rc}",
            meta={"returncode": rc, "backend": "grok"},
        )


# ---------------------------------------------------------------------------
# Optional multi-vendor: acpx (not Codex-required)
# ---------------------------------------------------------------------------


@dataclass
class AcpxParticipantBackend:
    """Run MoA participants via the acpx headless ACP CLI (read-only).

    Builds::

        acpx --format quiet --approve-reads [--cwd DIR] [--timeout N] \\
             <agent> exec <prompt>

    Never passes ``--approve-all``. Live authenticated agents are optional; the
    command construction is the contract tested in CI.
    """

    acpx_bin: str = "acpx"
    default_timeout: float | None = 300.0
    format: str = "quiet"

    def build_command(
        self,
        agent: str,
        prompt: str,
        *,
        cwd: str | None = None,
        permission: PermissionMode | str = DEFAULT_PARTICIPANT_PERMISSION,
        timeout: float | None = None,
    ) -> list[str]:
        mode = assert_participant_permission(permission)
        argv: list[str] = [self.acpx_bin, "--format", self.format]
        if mode == PermissionMode.APPROVE_READS.value:
            argv.append("--approve-reads")
        else:
            argv.append("--deny-all")
        if cwd:
            argv.extend(["--cwd", cwd])
        to = timeout if timeout is not None else self.default_timeout
        if to is not None:
            argv.extend(["--timeout", str(int(to))])
        argv.extend([agent, "exec", prompt])
        return argv

    def is_available(self) -> bool:
        if os.path.sep in self.acpx_bin:
            return os.path.isfile(self.acpx_bin) and os.access(self.acpx_bin, os.X_OK)
        return shutil.which(self.acpx_bin) is not None

    async def consult(
        self,
        agent: str,
        prompt: str,
        *,
        cwd: str | None = None,
        permission: str = DEFAULT_PARTICIPANT_PERMISSION.value,
        timeout: float | None = None,
    ) -> ParticipantOpinion:
        mode = assert_participant_permission(permission)
        full_prompt = READ_ONLY_PARTICIPANT_PREAMBLE + (prompt or "")
        argv = self.build_command(
            agent, full_prompt, cwd=cwd, permission=mode, timeout=timeout
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            return ParticipantOpinion(
                name=agent,
                text="",
                ok=False,
                permission_mode=mode,
                error=f"acpx not found: {e}",
            )
        stdout_b, stderr_b = await proc.communicate()
        stdout = (stdout_b or b"").decode("utf-8", errors="replace").strip()
        stderr = (stderr_b or b"").decode("utf-8", errors="replace").strip()
        rc = proc.returncode if proc.returncode is not None else -1
        if rc == 0 and stdout:
            return ParticipantOpinion(
                name=agent,
                text=stdout,
                ok=True,
                permission_mode=mode,
                meta={"returncode": rc},
            )
        err = stderr or stdout or f"acpx exited {rc}"
        return ParticipantOpinion(
            name=agent,
            text=stdout,
            ok=False,
            permission_mode=mode,
            error=err,
            meta={"returncode": rc, "stderr": stderr},
        )
