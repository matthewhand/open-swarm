"""Mixture of Agents blueprint — read-only CLI consensus via MoA orchestrator.

Primary model id: ``moa`` / ``mixture_of_agents``.
Legacy aliases: ``cli_fusion``, ``cli_ensemble`` (same blueprint class; read-only MoA only).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.moa import MoAOrchestrator, PermissionMode
from swarm.core.moa.backends import FakeParticipantBackend
from swarm.core.moa.cli import build_backend

logger = logging.getLogger(__name__)

# Legacy product names that resolve to MoA (read-only), not multi-writer fusion.
LEGACY_ALIASES = frozenset({"cli_fusion", "cli_ensemble", "fusion", "ensemble"})


class MoABlueprint(BlueprintBase):
    """Expose Mixture of Agents over the blueprint runner."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "moa",
        "title": "Mixture of Agents (read-only CLI consensus)",
        "description": (
            "Fan a question to N read-only participants (fake for CI, grok for live "
            "consensus, optional acpx for multi-vendor). Orchestrator determines "
            "consensus and alone may act/write. Codex is not required. "
            "Legacy aliases: cli_fusion, cli_ensemble."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["moa", "mixture-of-agents", "consensus", "readonly", "cli", "grok"],
        # Discoverable as model ids on /v1/models and /v1/chat/completions
        "aliases": sorted(LEGACY_ALIASES | {"mixture_of_agents"}),
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def __init__(self, blueprint_id: str = "moa", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})

    def _participants(self) -> list[str]:
        params = self._params
        moa_cfg = (self._config or {}).get("moa") or {}
        raw = params.get("participants") or moa_cfg.get("participants") or []
        if isinstance(raw, str):
            return [p.strip() for p in raw.split(",") if p.strip()]
        names = [str(p) for p in raw]
        if names:
            return names
        # Defaults: multi-seat labels for fake; single grok seat for live grok.
        kind = (params.get("backend") or moa_cfg.get("backend") or "fake").lower()
        if kind == "grok":
            return ["grok"]
        return ["analyst", "critic"]

    def _backend(self):
        """Resolve participant backend: fake (params/tests) | grok | acpx.

        Live first-class path is grok. Codex is not required.
        """
        params = self._params
        moa_cfg = (self._config or {}).get("moa") or {}
        timeout = float(
            params.get("timeout")
            or moa_cfg.get("default_timeout")
            or 300
        )
        if params.get("fake_responses"):
            return FakeParticipantBackend(dict(params["fake_responses"]))
        kind = (params.get("backend") or moa_cfg.get("backend") or "fake").lower()
        if kind == "fake":
            # Empty fake map → clear error from seats; tests should pass fake_responses.
            seats = self._participants()
            stubs = {
                n: f"(stub opinion from {n} — set params.fake_responses or backend=grok)"
                for n in seats
            }
            return FakeParticipantBackend(stubs)
        return build_backend(backend=kind, timeout=timeout)

    def _permission(self) -> str:
        moa_cfg = (self._config or {}).get("moa") or {}
        raw = self._params.get("permission") or moa_cfg.get("permission") or "approve-reads"
        if raw in (PermissionMode.APPROVE_ALL.value, "approve-all", "write"):
            # Hard clamp: MoA participants never get write approval.
            logger.warning("MoA clamped participant permission %r → approve-reads", raw)
            return PermissionMode.APPROVE_READS.value
        return str(raw)

    async def run(self, messages: list[dict[str, Any]], **kwargs) -> Any:
        question_parts = []
        for m in messages or []:
            if isinstance(m, dict) and m.get("content"):
                role = (m.get("role") or "user").upper()
                question_parts.append(f"{role}: {m['content']}")
        question = "\n\n".join(question_parts).strip()
        if not question:
            yield {"role": "assistant", "content": "No prompt provided.", "final": True}
            return

        participants = self._participants()
        if not participants:
            yield {
                "role": "assistant",
                "content": (
                    "No MoA participants configured. Set params.participants or "
                    "moa.participants (e.g. [\"grok\"] or [\"analyst\",\"critic\"])."
                ),
                "final": True,
            }
            return

        orch = MoAOrchestrator(
            backend=self._backend(),
            participant_permission=self._permission(),
        )
        # Determination always orchestrator-side (default synthesizer or inject later).
        result = await orch.run(
            question,
            participants,
            cwd=self._params.get("workdir") or self._params.get("cwd"),
            act=bool(self._params.get("act")),
            action=self._params.get("action"),
        )
        det = result.determination
        answer = det.answer if det else "No determination."
        ok_names = [o.name for o in result.ok_opinions]
        meta = {
            "moa": True,
            # system_fingerprint uses backends=… (orchestrator-owned panel that answered)
            "backends": ok_names,
            "participants": [o.name for o in result.opinions],
            "ok_participants": ok_names,
            "act": bool(result.act_result),
        }
        message = {"role": "assistant", "content": answer}
        # ChatCompletionsView accepts {messages: [...]} final shape + meta side-channel.
        yield {
            "messages": [message],
            "role": "assistant",
            "content": answer,
            "final": True,
            "meta": meta,
            "opinions": [
                {"name": o.name, "ok": o.ok, "text": o.text, "error": o.error}
                for o in result.opinions
            ],
        }


# Legacy model ids are registered via metadata["aliases"] only (no class aliases —
# those confused discovery with multi-subclass warnings).
