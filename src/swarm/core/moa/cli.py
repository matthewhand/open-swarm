"""CLI entry helpers for Mixture of Agents (used by ``swarm-cli moa``).

Keeps Typer/argparse surface thin: parse → orchestrate → print.
Supports:

* ``--backend fake`` — demos / CI (default)
* ``--backend grok`` — first-class live consensus via local ``grok -p``
* ``--backend acpx`` — optional multi-vendor CLIs (not required; Codex deferred)
"""

from __future__ import annotations

import json
import logging
from typing import Any

# Import from leaf modules (not package __init__) to avoid circular import:
# __init__ → agents_orchestrator → tools → cli → __init__
from swarm.core.moa.backends import (
    AcpxParticipantBackend,
    FakeParticipantBackend,
    GrokParticipantBackend,
    RecordingWriteSurface,
)
from swarm.core.moa.orchestrator import MoAOrchestrator
from swarm.core.moa.types import ActResult, PermissionMode

logger = logging.getLogger(__name__)

# Re-export for callers that imported Grok from this module historically.
__all__ = [
    "GrokParticipantBackend",
    "build_backend",
    "format_moa_text",
    "parse_fake_responses",
    "run_moa_cli",
]


def parse_fake_responses(raw: str | None) -> dict[str, str]:
    """Parse ``name=text`` pairs separated by ``||`` or a JSON object."""
    if not raw:
        return {}
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"--fake-responses looks like JSON but failed to parse: {e}"
            ) from e
        if not isinstance(data, dict):
            raise ValueError(
                "--fake-responses JSON must be an object of name→text pairs"
            )
        return {str(k): str(v) for k, v in data.items()}
    out: dict[str, str] = {}
    for part in raw.split("||"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(
                "--fake-responses entries must be name=text "
                f"(pairs separated by ||) or a JSON object; got {part!r}"
            )
        name, text = part.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(
                "--fake-responses entries must be name=text; "
                f"missing name before '=': {part!r}"
            )
        out[name] = text.strip()
    return out


def build_backend(
    *,
    backend: str,
    fake_responses: dict[str, str] | None = None,
    timeout: float = 300.0,
) -> Any:
    """Construct a participant backend for the moa CLI."""
    kind = (backend or "fake").lower()
    if kind == "fake":
        if not fake_responses:
            raise ValueError(
                "--backend fake requires --fake-responses "
                "(name=text pairs separated by ||, or a JSON object)"
            )
        return FakeParticipantBackend(fake_responses)
    if kind == "grok":
        return GrokParticipantBackend(default_timeout=timeout)
    if kind == "acpx":
        return AcpxParticipantBackend(default_timeout=timeout)
    raise ValueError(
        f"unknown --backend {backend!r}; choose one of: fake, grok, acpx"
    )


async def run_moa_cli(
    question: str,
    participants: list[str],
    *,
    backend: str = "fake",
    fake_responses: dict[str, str] | None = None,
    cwd: str | None = None,
    permission: str = PermissionMode.APPROVE_READS.value,
    timeout: float = 300.0,
    act: bool = False,
    action: str | None = None,
    act_write_path: str | None = None,
    json_out: bool = False,
    trace_path: str | None = None,
) -> dict[str, Any]:
    """Run MoA and return a serializable result dict (also used by tests)."""
    from swarm.core.moa.schema import parse_proposal

    be = build_backend(
        backend=backend, fake_responses=fake_responses, timeout=timeout
    )
    write_surface = RecordingWriteSurface()

    async def act_fn(determination, action_text: str) -> ActResult:
        # Default filename when --act is set without --act-write.
        path = act_write_path or "moa_determination.md"
        content = (
            f"# MoA determination\n\nAction: {action_text}\n\n"
            f"{determination.answer}\n"
        )
        # Only orchestrator path may write; always persist (not record-only).
        write_surface.write(path, content)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ActResult(ok=True, detail=f"wrote {path}", side_effects=[path])

    orch = MoAOrchestrator(
        backend=be,
        act_fn=act_fn if act else None,
        participant_permission=permission,
    )
    result = await orch.run(
        question,
        participants,
        cwd=cwd,
        act=act,
        action=action or "record determination",
    )
    opinions_payload = []
    for o in result.opinions:
        prop = parse_proposal(o.text) if o.ok else None
        opinions_payload.append(
            {
                "name": o.name,
                "ok": o.ok,
                "text": o.text,
                "error": o.error,
                "permission_mode": o.permission_mode,
                "proposal": prop.as_dict() if prop else None,
            }
        )
    payload = {
        "question": question,
        "participants": participants,
        "backend": backend,
        "permission": permission,
        "opinions": opinions_payload,
        "determination": (
            {
                "answer": result.determination.answer,
                "rationale": result.determination.rationale,
                "participant_names": result.determination.participant_names,
                "analysis": result.determination.analysis,
            }
            if result.determination
            else None
        ),
        "act": (
            {
                "ok": result.act_result.ok,
                "detail": result.act_result.detail,
                "side_effects": result.act_result.side_effects,
            }
            if result.act_result
            else None
        ),
        "writes": list(write_surface.writes),
        # Path A markers (parity with team_result_to_payload / --team JSON).
        # Panel seats never write; specialists only exist on consensus_then_team.
        # --act is not consensus_only: stamp consensus_then_act so CLI human
        # output routes to format_moa_text (## Act) instead of format_team_text.
        "mode": "consensus_then_act" if act else "consensus_only",
        "specialists": [],
        "panel_wrote": False,
    }
    if trace_path:
        from pathlib import Path

        payload["trace_path"] = trace_path
        out = Path(trace_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def format_moa_text(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    mode = payload.get("mode")
    if mode:
        lines.append(f"MoA mode: {mode}")
    lines.append(f"MoA question: {payload.get('question', '')}")
    lines.append(f"backend={payload.get('backend')} permission={payload.get('permission')}")
    lines.append("")
    lines.append("## Opinions (read-only participants)")
    for o in payload.get("opinions") or []:
        status = "ok" if o.get("ok") else f"FAIL: {o.get('error')}"
        lines.append(f"### {o.get('name')} [{status}] perm={o.get('permission_mode')}")
        lines.append((o.get("text") or "").strip() or "(empty)")
        lines.append("")
    det = payload.get("determination") or {}
    lines.append("## Determination (orchestrator only)")
    lines.append((det.get("answer") or "(none)").strip())
    if det.get("rationale"):
        lines.append("")
        lines.append(f"_rationale:_ {det['rationale']}")
    if payload.get("act"):
        lines.append("")
        lines.append(f"## Act: {payload['act']}")
    return "\n".join(lines).rstrip() + "\n"
