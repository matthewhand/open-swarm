"""Safety role: classify a pending tool call and (API chat only) elicit approval.

This is the REQ-55 surface. Internal aliases ``gate`` / ``tool_gate`` stay so
REQ-9 / PR 314 can land later without a rename fight. User-facing copy is
**Safety**.

Default-open (same as REQ-9):

* No safety role assigned → every tool call is approved; never prompt.
* Safety assigned but unconcerned (NO) → run the tool; never prompt.
* Safety assigned and concerned (YES) → pause for Allow once / Always allow /
  Deny. ``Always allow`` persists for that tool name on this agent (v1).

CLI and remote (Herdr / harness) sessions keep their own approval UIs.
:func:`uses_swarm_approval` is the single gate: those channels never elicit.
"""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from swarm.core.paths import get_user_data_dir_for_swarm

logger = logging.getLogger(__name__)

CHANNEL_API = "api"
CHANNEL_CLI = "cli"
CHANNEL_REMOTE = "remote"

SWARM_APPROVAL_CHANNELS = frozenset({CHANNEL_API})

# Blueprint / member kinds that must never hit swarm approval.
CLI_BLUEPRINT_IDS = frozenset({
    "cli_agent",
    "cli_fusion",
    "cli_orchestrator",
    "cli_map",
    "cli_planner",
})
REMOTE_BLUEPRINT_IDS = frozenset({
    "remote_harness",
    "herdr",
})
REMOTE_MEMBER_KINDS = frozenset({
    "herdr",
    "remote",
    "hermes",
    "omb",
    "rakazo",
})

SAFETY_ROLE_ALIASES = frozenset({
    "safety",
    "gate",
    "tool_gate",
    "tool-gate",
    "toolgate",
})

_CONCERNED_TOKENS = frozenset({"YES", "Y", "DANGEROUS", "CONCERNED", "TRUE", "1"})
_SAFE_TOKENS = frozenset({"NO", "N", "SAFE", "UNCONCERNED", "FALSE", "0"})

ALWAYS_ALLOW_ENV = "SWARM_SAFETY_ALWAYS_ALLOW_PATH"

ClassifyFn = Callable[[str, dict[str, Any]], bool]
ElicitFn = Callable[[str, dict[str, Any]], Any]
EmitFn = Callable[[dict[str, Any]], Any]
InvokeFn = Callable[[Any, str], str]


def uses_swarm_approval(channel: str | None) -> bool:
    """True only for API-agent chat. CLI and remote never elicit here."""
    return (channel or CHANNEL_API).strip().lower() in SWARM_APPROVAL_CHANNELS


def channel_for_runtime(
    *,
    blueprint_id: str | None = None,
    member_kind: str | None = None,
    params: dict[str, Any] | None = None,
) -> str:
    """Resolve api / cli / remote from the running blueprint or team member."""
    kind = str(member_kind or (params or {}).get("kind") or "").strip().lower()
    if kind == "cli":
        return CHANNEL_CLI
    if kind in REMOTE_MEMBER_KINDS:
        return CHANNEL_REMOTE
    bp = str(blueprint_id or (params or {}).get("blueprint") or "").strip().lower()
    if bp in CLI_BLUEPRINT_IDS or bp.startswith("cli_"):
        return CHANNEL_CLI
    if bp in REMOTE_BLUEPRINT_IDS:
        return CHANNEL_REMOTE
    return CHANNEL_API


def normalize_safety_role(value: Any) -> str | None:
    """Return ``safety`` when *value* is a gate/safety alias; else ``None``."""
    if value is None:
        return None
    key = str(value).strip().lower().replace(" ", "_")
    if key in SAFETY_ROLE_ALIASES:
        return "safety"
    return None


def is_safety_role(value: Any) -> bool:
    return normalize_safety_role(value) == "safety"


def _agent_role(agent: Any) -> str:
    if agent is None:
        return ""
    if isinstance(agent, dict):
        return str(agent.get("role") or agent.get("id") or agent.get("name") or "")
    return str(
        getattr(agent, "role", None)
        or getattr(agent, "id", None)
        or getattr(agent, "name", None)
        or ""
    )


def safety_role_assigned(agents: Any = None, *, metadata: dict[str, Any] | None = None) -> bool:
    """True when a safety / gate / tool_gate seat is on the roster."""
    meta = metadata or {}
    if is_safety_role(meta.get("role")):
        return True
    if meta.get("gate_agent") or meta.get("safety_agent"):
        return True
    if agents is None:
        agents = meta.get("agents")
    if agents is None:
        return False
    items: Iterable[Any]
    if isinstance(agents, dict):
        items = agents.values()
    else:
        items = agents
    for agent in items:
        if is_safety_role(_agent_role(agent)):
            return True
        if isinstance(agent, dict) and (
            is_safety_role(agent.get("id")) or is_safety_role(agent.get("name"))
        ):
            return True
    return False


def parse_safety_token(text: Any) -> bool:
    """Parse a YES/NO reply as *concerned* (dangerous). Empty / ambiguous → False."""
    if isinstance(text, bool):
        return text
    if isinstance(text, dict):
        for key in ("concerned", "dangerous", "is_dangerous", "yes", "deny"):
            if key in text:
                return bool(text[key])
        if "approved" in text:
            return not bool(text["approved"])
        text = text.get("token") or text.get("answer") or text.get("content") or ""
    raw = str(text or "").strip()
    parts = raw.split()
    if not parts:
        return False
    token = parts[0].upper().strip(".,!?;:\"'")
    if token in _CONCERNED_TOKENS:
        return True
    if token in _SAFE_TOKENS:
        return False
    return False


def _safety_prompt(tool_name: str, arguments: dict[str, Any] | None) -> str:
    return (
        "Is this pending tool call concerning?\n"
        f"Tool: {tool_name}\n"
        f"Arguments: {arguments or {}}\n"
        "Reply YES or NO only."
    )


@dataclass
class SafetyVerdict:
    """Classification + approval outcome for one pending tool call."""

    concerned: bool
    approved: bool = True
    prompted: bool = False
    raw: str = ""
    always_allowed: bool = False
    channel: str = CHANNEL_API


@dataclass
class AlwaysAllowStore:
    """Persist ``Always allow`` for ``(agent_id, tool_name)`` (v1, no arg fingerprint)."""

    path: Path | None = None
    _allowed: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path is not None:
            self.load()

    def is_allowed(self, agent_id: str, tool_name: str) -> bool:
        return tool_name in self._allowed.get(agent_id, set())

    def allow(self, agent_id: str, tool_name: str) -> None:
        self._allowed.setdefault(agent_id, set()).add(tool_name)
        self.save()

    def load(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.info("safety always-allow store unreadable; starting empty")
            return
        if not isinstance(payload, dict):
            return
        next_map: dict[str, set[str]] = {}
        for agent_id, names in payload.items():
            if isinstance(names, list):
                next_map[str(agent_id)] = {str(n) for n in names if n}
        self._allowed = next_map

    def save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            blob = {agent: sorted(names) for agent, names in self._allowed.items()}
            self.path.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
        except OSError:
            logger.info("safety always-allow store not writable")


def default_always_allow_path() -> Path:
    env = (os.environ.get(ALWAYS_ALLOW_ENV) or "").strip()
    if env:
        return Path(env)
    return get_user_data_dir_for_swarm() / "safety_always_allow.json"


def classify_pending_tool_call(
    *,
    safety: Any = None,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    safety_assigned: bool | None = None,
) -> SafetyVerdict:
    """Return whether *tool_name* is concerning. Unwired → not concerned."""
    assigned = (
        bool(safety_assigned)
        if safety_assigned is not None
        else (safety is not None or classify_fn is not None)
    )
    args = arguments or {}
    if not assigned:
        return SafetyVerdict(concerned=False, raw="UNWIRED", approved=True)

    raw = ""
    try:
        if classify_fn is not None:
            concerned = bool(classify_fn(tool_name, args))
            raw = "YES" if concerned else "NO"
        elif safety is not None:
            raw = _invoke_safety_agent(safety, _safety_prompt(tool_name, args), invoke_fn=invoke_fn)
            concerned = parse_safety_token(raw)
        else:
            return SafetyVerdict(concerned=False, raw="UNWIRED", approved=True)
    except Exception as exc:
        logger.info("wired safety failed to classify %s (%s); treating as concerned", tool_name, exc)
        concerned = True
        raw = f"ERROR: {exc}"
    return SafetyVerdict(concerned=concerned, raw=str(raw), approved=not concerned)


def _invoke_safety_agent(safety: Any, prompt: str, *, invoke_fn: InvokeFn | None = None) -> str:
    if invoke_fn is not None:
        return str(invoke_fn(safety, prompt))
    for attr in ("classify", "respond"):
        fn = getattr(safety, attr, None)
        if callable(fn):
            return str(fn(prompt))
    as_tool = getattr(safety, "as_tool", None)
    if callable(as_tool):
        try:
            tool = as_tool(
                tool_name=getattr(safety, "name", None) or "safety",
                tool_description="Classify a pending tool call as concerning or not.",
            )
            on_invoke = getattr(tool, "on_invoke_tool", None)
            if callable(on_invoke):
                result = on_invoke(None, prompt)
                return str(result)
        except Exception as exc:
            logger.debug("safety as_tool invoke skipped: %s", exc)
    raise RuntimeError("safety agent has no classify / as_tool invoke path")


def approve_pending_tool_call(
    *,
    channel: str = CHANNEL_API,
    safety: Any = None,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    agent_id: str = "",
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
    always_allow: AlwaysAllowStore | None = None,
    safety_assigned: bool | None = None,
) -> SafetyVerdict:
    """Approve a pending tool call.

    CLI/remote: approved, **elicit_fn is not called**.
    Unwired (no safety assigned): approved, no prompt.
    Wired + unconcerned: approved, no prompt.
    Always-allowed tool name on this agent: approved, no prompt.
    Wired + concerned: ``elicit_fn`` is called; missing elicit → denied.
    """
    args = arguments or {}
    if not uses_swarm_approval(channel):
        return SafetyVerdict(
            concerned=False,
            raw="CHANNEL_SKIP",
            approved=True,
            prompted=False,
            channel=channel,
        )

    assigned = (
        bool(safety_assigned)
        if safety_assigned is not None
        else (safety is not None or classify_fn is not None)
    )
    if not assigned:
        return SafetyVerdict(
            concerned=False,
            raw="UNWIRED",
            approved=True,
            prompted=False,
            channel=channel,
        )

    if always_allow is not None and agent_id and always_allow.is_allowed(agent_id, tool_name):
        return SafetyVerdict(
            concerned=False,
            raw="ALWAYS_ALLOW",
            approved=True,
            prompted=False,
            always_allowed=True,
            channel=channel,
        )

    classified = classify_pending_tool_call(
        safety=safety,
        tool_name=tool_name,
        arguments=args,
        classify_fn=classify_fn,
        invoke_fn=invoke_fn,
        safety_assigned=True,
    )
    classified.channel = channel
    if not classified.concerned:
        classified.approved = True
        classified.prompted = False
        return classified

    prompted = False
    approved = False
    if elicit_fn is not None:
        prompted = True
        decision = elicit_fn(tool_name, args)
        approved, persist = _interpret_decision(decision)
        if persist and always_allow is not None and agent_id:
            always_allow.allow(agent_id, tool_name)
    classified.prompted = prompted
    classified.approved = approved
    return classified


def _interpret_decision(decision: Any) -> tuple[bool, bool]:
    """Map an elicit result to ``(approved, persist_always_allow)``."""
    if isinstance(decision, bool):
        return decision, False
    token = str(decision or "").strip().lower()
    if token in {"allow", "allow_once", "once", "yes", "y", "approve"}:
        return True, False
    if token in {"always", "always_allow", "always-allow"}:
        return True, True
    return False, False


def wrap_tools_with_safety(
    tools: list[Any] | None,
    *,
    channel: str = CHANNEL_API,
    safety: Any = None,
    classify_fn: ClassifyFn | None = None,
    elicit_fn: ElicitFn | None = None,
    always_allow: AlwaysAllowStore | None = None,
    agent_id: str = "",
    safety_assigned: bool | None = None,
) -> list[Any]:
    """Wrap callables for API + assigned safety. CLI/remote / unwired → unchanged."""
    if not tools:
        return list(tools or [])
    assigned = (
        bool(safety_assigned)
        if safety_assigned is not None
        else (safety is not None or classify_fn is not None)
    )
    if not uses_swarm_approval(channel) or not assigned:
        return list(tools)

    wrapped: list[Any] = []
    for tool in tools:
        name = (
            getattr(tool, "name", None)
            or getattr(tool, "__name__", None)
            or type(tool).__name__
        )
        if callable(tool) and not hasattr(tool, "on_invoke_tool"):
            wrapped.append(
                _wrap_callable(
                    tool,
                    tool_name=str(name),
                    channel=channel,
                    safety=safety,
                    classify_fn=classify_fn,
                    elicit_fn=elicit_fn,
                    always_allow=always_allow,
                    agent_id=agent_id,
                )
            )
        else:
            wrapped.append(tool)
    return wrapped


def _wrap_callable(
    fn: Callable[..., Any],
    *,
    tool_name: str,
    channel: str,
    safety: Any,
    classify_fn: ClassifyFn | None,
    elicit_fn: ElicitFn | None,
    always_allow: AlwaysAllowStore | None,
    agent_id: str,
) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        verdict = approve_pending_tool_call(
            channel=channel,
            safety=safety,
            tool_name=tool_name,
            arguments={"args": args, "kwargs": kwargs},
            agent_id=agent_id,
            classify_fn=classify_fn,
            elicit_fn=elicit_fn,
            always_allow=always_allow,
            safety_assigned=True,
        )
        if not verdict.approved:
            return f"DENIED: tool call {tool_name!r} was not approved"
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", tool_name)
    wrapped.__doc__ = getattr(fn, "__doc__", None)
    return wrapped


@dataclass
class SafetySession:
    """Per-run hook installed by the API chat consumer (not CLI/remote)."""

    agent_id: str = ""
    channel: str = CHANNEL_API
    safety_assigned: bool = False
    safety: Any = None
    classify_fn: ClassifyFn | None = None
    elicit_fn: ElicitFn | None = None
    emit_fn: EmitFn | None = None
    always_allow: AlwaysAllowStore | None = None

    def uses_swarm_approval(self) -> bool:
        return uses_swarm_approval(self.channel)

    def emit(self, payload: dict[str, Any]) -> None:
        if self.emit_fn is None:
            return
        try:
            result = self.emit_fn(payload)
            if hasattr(result, "__await__"):
                # Consumer emit is scheduled by the caller when async.
                pass
        except Exception:
            logger.debug("safety emit skipped", exc_info=True)

    def approve(self, tool_name: str, arguments: dict[str, Any] | None = None) -> SafetyVerdict:
        return approve_pending_tool_call(
            channel=self.channel,
            safety=self.safety,
            tool_name=tool_name,
            arguments=arguments,
            agent_id=self.agent_id,
            classify_fn=self.classify_fn,
            elicit_fn=self.elicit_fn,
            always_allow=self.always_allow,
            safety_assigned=self.safety_assigned,
        )

    async def approve_async(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> SafetyVerdict:
        return await approve_pending_tool_call_async(
            channel=self.channel,
            safety=self.safety,
            tool_name=tool_name,
            arguments=arguments,
            agent_id=self.agent_id,
            classify_fn=self.classify_fn,
            elicit_fn=self.elicit_fn,
            always_allow=self.always_allow,
            safety_assigned=self.safety_assigned,
        )


_CURRENT_SESSION: ContextVar[SafetySession | None] = ContextVar(
    "swarm_safety_session",
    default=None,
)


def current_safety_session() -> SafetySession | None:
    return _CURRENT_SESSION.get()


def install_safety_session(session: SafetySession | None):
    return _CURRENT_SESSION.set(session)


def reset_safety_session(token) -> None:
    _CURRENT_SESSION.reset(token)


async def maybe_await(value: Any) -> Any:
    if isinstance(value, Awaitable):
        return await value
    return value


async def approve_pending_tool_call_async(
    *,
    channel: str = CHANNEL_API,
    safety: Any = None,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    agent_id: str = "",
    classify_fn: ClassifyFn | None = None,
    invoke_fn: InvokeFn | None = None,
    elicit_fn: ElicitFn | None = None,
    always_allow: AlwaysAllowStore | None = None,
    safety_assigned: bool | None = None,
) -> SafetyVerdict:
    """Async variant so chat can wait on a websocket Allow / Deny decision."""

    def _elicit(name: str, args: dict[str, Any]) -> Any:
        if elicit_fn is None:
            return False
        return elicit_fn(name, args)

    # First pass without elicit to see if we must prompt. If elicit is async,
    # run classify/always-allow the same way as the sync helper, then await.
    preview = approve_pending_tool_call(
        channel=channel,
        safety=safety,
        tool_name=tool_name,
        arguments=arguments,
        agent_id=agent_id,
        classify_fn=classify_fn,
        invoke_fn=invoke_fn,
        elicit_fn=None,
        always_allow=always_allow,
        safety_assigned=safety_assigned,
    )
    if not preview.concerned or preview.always_allowed or not uses_swarm_approval(channel):
        return preview
    if safety_assigned is False or (
        safety_assigned is None and safety is None and classify_fn is None
    ):
        return preview
    if elicit_fn is None:
        preview.approved = False
        preview.prompted = False
        return preview
    decision = await maybe_await(_elicit(tool_name, arguments or {}))
    approved, persist = _interpret_decision(decision)
    if persist and always_allow is not None and agent_id:
        always_allow.allow(agent_id, tool_name)
    preview.prompted = True
    preview.approved = approved
    return preview
