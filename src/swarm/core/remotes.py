"""Remote agent-harness connectivity: Hermes, OpenMausBot (OMB), Rakazo.

Open Swarm is a harness *for* other harnesses. This module is the single
source of truth for:

* persisted ``remotes`` config (base URL + auth)
* honest health/version probes (one request, no retry/crash-loop)
* operate: list / send a job via each harness's real HTTP API

LAN defaults are operator facts (ubuntu-gtx / Windows2). They are not
invented cloud hosts. Do **not** point these remotes at Fly open-litellm;
the LAN LLM for *this* swarm is ``http://10.0.0.30:8000/v1``.

Auth is optional per remote. Missing auth is reported honestly; we never
enable ``SWARM_ALLOW_ANONYMOUS`` and we never clone OMB source.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

REMOTE_IDS: tuple[str, ...] = ("hermes", "omb", "rakazo")

# Team (REQ-11 vocabulary): agents that SEE and TALK to each other via
# openai-agents handoff / as_tool. This is NOT the /teams/ LLM-profile alias
# registry (DynamicTeamBlueprint). Remotes are Team *members*.
TEAM_VOCABULARY: dict[str, str] = {
    "team": (
        "A Team wires API agents, CLI agents, and remote agents "
        "(Hermes / OMB / Rakazo) so they can see and talk to each other "
        "via openai-agents handoff or as_tool."
    ),
    "not_teams_page": (
        "The Django /teams/ JSON registry is LLM-profile aliases "
        "(DynamicTeamBlueprint) — not this Team. Prefer 'Profiles' for that surface."
    ),
}

_TOOL_NAMES: dict[str, str] = {
    "hermes": "consult_hermes",
    "omb": "consult_omb",
    "rakazo": "consult_rakazo",
}

# Verified operator LAN facts (not reachable from every cloud VM).
_DEFAULTS: dict[str, dict[str, Any]] = {
    "hermes": {
        "title": "Hermes Agent (ubuntu-gtx)",
        "host_label": "ubuntu-gtx",
        "base_url": "http://10.0.0.36:8642",
        "ui_url": "http://10.0.0.36:9119",
        "api_key": "${HERMES_API_KEY}",
        "health_path": "/health",
        "version_path": "/v1/models",
        "notes": (
            "Nous Hermes gateway on :8642 (GET /health, GET /v1/models, "
            "POST /v1/runs, GET /api/sessions, GET /api/jobs). Dashboard :9119 "
            "is operator chrome, not the operate API. Do not bounce Hermes "
            "to read config; do not delete SKILL.md on that box."
        ),
    },
    "omb": {
        "title": "OpenMausBot (Windows2)",
        "host_label": "Windows2",
        "base_url": "http://10.0.0.32:8802",
        "ui_url": "",
        "api_key": "${OMB_API_KEY}",
        "health_path": "/api/health",
        "version_path": "/api/health",
        "notes": (
            "OpenMausBot harness on :8802 (upstream default is :8799). "
            "GET /api/health, GET /api/bots, POST /api/bots, "
            "POST /api/bots/{id}/messages starts a turn (202). "
            "We talk HTTP only — no OMB source clone."
        ),
    },
    "rakazo": {
        "title": "Rakazo (Windows2)",
        "host_label": "Windows2",
        "base_url": "http://10.0.0.32:3100",
        "ui_url": "http://10.0.0.32:5173",
        "api_key": "${RAKAZO_API_KEY}",
        "cookie": "${RAKAZO_SESSION_COOKIE}",
        "health_path": "/health",
        "version_path": "/health",
        "notes": (
            "Rakazo API :3100, Vite UI :5173, tree C:\\rakazo. "
            "GET /health is public. bots.list / threads.send live under "
            "/rpc/* and require a Better Auth session (cookie or bearer). "
            "Health works without auth; operate fails honestly on 401."
        ),
    },
}

_ENV_BASE = {
    "hermes": "HERMES_BASE_URL",
    "omb": "OMB_BASE_URL",
    "rakazo": "RAKAZO_BASE_URL",
}
_ENV_KEY = {
    "hermes": "HERMES_API_KEY",
    "omb": "OMB_API_KEY",
    "rakazo": "RAKAZO_API_KEY",
}
_ENV_UI = {"rakazo": "RAKAZO_UI_URL", "hermes": "HERMES_UI_URL"}
_ENV_COOKIE = {"rakazo": "RAKAZO_SESSION_COOKIE"}

_UP = frozenset({200, 201, 202, 204})
_AUTH = frozenset({401, 403})
_FORBIDDEN_BASE_HINTS = ("fly.dev", "open-litellm", "openlitellm")

_DEFAULT_TIMEOUT_S = 3.0
_OPERATE_TIMEOUT_S = 8.0


class RemoteError(Exception):
    """Non-crash failure talking to a remote harness."""


@dataclass
class RemoteSpec:
    """Persisted + resolved connection for one remote harness."""

    id: str
    title: str
    host_label: str
    base_url: str
    ui_url: str = ""
    api_key: str = ""
    cookie: str = ""
    health_path: str = "/health"
    version_path: str = "/health"
    notes: str = ""
    source: str = "default"

    def origin(self) -> tuple[str, int]:
        parsed = urlparse(self.base_url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return host, int(port)

    def public_dict(self) -> dict[str, Any]:
        """JSON-safe view with secrets redacted."""
        return {
            "id": self.id,
            "title": self.title,
            "host_label": self.host_label,
            "base_url": self.base_url,
            "ui_url": self.ui_url,
            "api_key_set": bool(self.api_key and not _is_unresolved_placeholder(self.api_key)),
            "cookie_set": bool(self.cookie and not _is_unresolved_placeholder(self.cookie)),
            "health_path": self.health_path,
            "version_path": self.version_path,
            "notes": self.notes,
            "source": self.source,
            "member": {
                "kind": "remote",
                "talk": _TOOL_NAMES[self.id],
                "via": "as_tool",
                "place_in": "Team (handoff members — not /teams/ profile aliases)",
            },
        }


@dataclass
class HealthResult:
    remote: str
    ok: bool
    state: str
    detail: str
    http_status: int | None = None
    version: Any = None
    latency_ms: int | None = None
    url: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperateResult:
    remote: str
    op: str
    ok: bool
    detail: str
    http_status: int | None = None
    data: Any = None
    gap: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HttpResult:
    status: int | None
    body: Any = None
    text: str = ""
    error: str = ""
    url: str = ""
    latency_ms: int = 0
    headers: dict[str, str] = field(default_factory=dict)


def _is_unresolved_placeholder(value: str) -> bool:
    raw = (value or "").strip()
    return raw.startswith("${") and raw.endswith("}") and len(raw) > 3


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        if _is_unresolved_placeholder(expanded):
            return ""
        return expanded
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _looks_like_forbidden_llm_proxy(url: str) -> bool:
    lowered = (url or "").lower()
    return any(hint in lowered for hint in _FORBIDDEN_BASE_HINTS)


def _normalize_base_url(url: str) -> str:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"http://{raw}"
    return raw


def default_spec(remote_id: str) -> RemoteSpec:
    rid = _require_id(remote_id)
    raw = dict(_DEFAULTS[rid])
    return RemoteSpec(id=rid, source="default", **raw)


def _require_id(remote_id: str) -> str:
    rid = (remote_id or "").strip().lower()
    aliases = {"openmausbot": "omb", "openmaus": "omb", "rakoza": "rakazo"}
    rid = aliases.get(rid, rid)
    if rid not in REMOTE_IDS:
        raise RemoteError(f"Unknown remote '{remote_id}'. Known: {', '.join(REMOTE_IDS)}")
    return rid


def resolve_config_path(explicit: str | Path | None = None) -> Path:
    """Path we read/write remotes from. Prefers existing file, else XDG."""
    from swarm.core.config_loader import find_config_file
    from swarm.core.paths import get_user_config_dir_for_swarm

    if explicit:
        return Path(explicit).expanduser()
    found = find_config_file()
    if found:
        return found
    return get_user_config_dir_for_swarm() / "swarm_config.json"


def load_raw_config(config_path: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    path = resolve_config_path(config_path)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data, path
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("remotes: failed to read %s: %s", path, exc)
    return {}, path


def load_remote(remote_id: str, config: dict[str, Any] | None = None) -> RemoteSpec:
    """Defaults ← swarm_config.json remotes ← env (env wins)."""
    rid = _require_id(remote_id)
    spec = default_spec(rid)
    cfg = config if isinstance(config, dict) else load_raw_config()[0]
    block = (cfg.get("remotes") or {}).get(rid) if isinstance(cfg.get("remotes"), dict) else None
    if isinstance(block, dict):
        spec.source = "config"
        for key in ("title", "host_label", "base_url", "ui_url", "api_key", "cookie", "health_path", "version_path", "notes"):
            if key in block and block[key] is not None:
                setattr(spec, key, block[key])
    env_base = os.environ.get(_ENV_BASE[rid], "").strip()
    if env_base:
        spec.base_url = env_base
        spec.source = "env"
    env_key = os.environ.get(_ENV_KEY[rid], "").strip()
    if env_key:
        spec.api_key = env_key
    env_ui = _ENV_UI.get(rid)
    if env_ui and os.environ.get(env_ui, "").strip():
        spec.ui_url = os.environ[env_ui].strip()
    env_cookie = _ENV_COOKIE.get(rid)
    if env_cookie and os.environ.get(env_cookie, "").strip():
        spec.cookie = os.environ[env_cookie].strip()

    spec.base_url = _normalize_base_url(_expand(spec.base_url))
    spec.ui_url = _normalize_base_url(_expand(spec.ui_url)) if spec.ui_url else ""
    spec.api_key = str(_expand(spec.api_key) or "")
    spec.cookie = str(_expand(spec.cookie) or "")
    spec.health_path = spec.health_path or "/health"
    spec.version_path = spec.version_path or spec.health_path
    if not spec.health_path.startswith("/"):
        spec.health_path = "/" + spec.health_path
    if not spec.version_path.startswith("/"):
        spec.version_path = "/" + spec.version_path
    return spec


def load_all_remotes(config: dict[str, Any] | None = None) -> dict[str, RemoteSpec]:
    cfg = config if isinstance(config, dict) else load_raw_config()[0]
    return {rid: load_remote(rid, cfg) for rid in REMOTE_IDS}


def load_placed_members(config: dict[str, Any] | None = None) -> list[str]:
    """Remote ids currently placed in the handoff Team (not /teams/ aliases).

    Missing ``agent_team.members`` means all three remotes are placed (default
    REQ-11 roster). An explicit empty list is an empty Team.
    """
    cfg = config if isinstance(config, dict) else load_raw_config()[0]
    block = cfg.get("agent_team") if isinstance(cfg.get("agent_team"), dict) else {}
    if "members" not in block:
        return list(REMOTE_IDS)
    raw = block.get("members") or []
    if not isinstance(raw, list):
        return list(REMOTE_IDS)
    out: list[str] = []
    for item in raw:
        try:
            rid = _require_id(str(item))
        except RemoteError:
            continue
        if rid not in out:
            out.append(rid)
    return out


def list_team_members(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Remote harnesses as Team members (handoff / as_tool), not profile aliases."""
    cfg = config if isinstance(config, dict) else load_raw_config()[0]
    placed = set(load_placed_members(cfg))
    members = []
    for spec in load_all_remotes(cfg).values():
        pub = spec.public_dict()
        members.append(
            {
                "id": spec.id,
                "kind": "remote",
                "title": spec.title,
                "base_url": spec.base_url,
                "talk": pub["member"]["talk"],
                "via": "as_tool",
                "placed": spec.id in placed,
            }
        )
    return members


def agent_team_public(
    config: dict[str, Any] | None = None,
    *,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    """Handoff Team roster (not /v1/teams/ Profiles aliases)."""
    cfg = config if isinstance(config, dict) else load_raw_config(config_path)[0]
    return {
        "object": "agent_team",
        "vocabulary": TEAM_VOCABULARY,
        "members": load_placed_members(cfg),
        "team_members": list_team_members(cfg),
        "not": "/v1/teams/ LLM-profile aliases (Profiles)",
    }


def persist_agent_team(
    members: list[str],
    *,
    config_path: str | Path | None = None,
) -> tuple[list[str], Path]:
    """Persist which remotes sit in the handoff Team (``agent_team.members``)."""
    resolved: list[str] = []
    for item in members:
        rid = _require_id(str(item))
        if rid not in resolved:
            resolved.append(rid)
    cfg, path = load_raw_config(config_path)
    if "llm" not in cfg or not isinstance(cfg.get("llm"), dict):
        cfg.setdefault("llm", {})
    team = cfg.get("agent_team") if isinstance(cfg.get("agent_team"), dict) else {}
    team = dict(team)
    team["members"] = resolved
    cfg["agent_team"] = team
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=4) + "\n", encoding="utf-8")
    logger.info("Persisted agent_team.members=%s to %s", resolved, path)
    return resolved, path


def place_team_member(remote_id: str, *, config_path: str | Path | None = None) -> tuple[list[str], Path]:
    rid = _require_id(remote_id)
    cfg, path = load_raw_config(config_path)
    current = load_placed_members(cfg)
    if rid not in current:
        current.append(rid)
    return persist_agent_team(current, config_path=path)


def unplace_team_member(remote_id: str, *, config_path: str | Path | None = None) -> tuple[list[str], Path]:
    rid = _require_id(remote_id)
    cfg, path = load_raw_config(config_path)
    current = [m for m in load_placed_members(cfg) if m != rid]
    return persist_agent_team(current, config_path=path)


def persist_remote(
    remote_id: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    ui_url: str | None = None,
    cookie: str | None = None,
    config_path: str | Path | None = None,
) -> tuple[RemoteSpec, Path]:
    """Merge fields into ``remotes.<id>`` and write swarm_config.json."""
    rid = _require_id(remote_id)
    cfg, path = load_raw_config(config_path)
    remotes = cfg.setdefault("remotes", {})
    if not isinstance(remotes, dict):
        remotes = {}
        cfg["remotes"] = remotes
    entry = remotes.get(rid) if isinstance(remotes.get(rid), dict) else {}
    entry = dict(entry)
    if "llm" not in cfg or not isinstance(cfg.get("llm"), dict):
        cfg.setdefault("llm", {})
    if base_url is not None:
        normalized = _normalize_base_url(base_url)
        if _looks_like_forbidden_llm_proxy(normalized):
            raise RemoteError(
                "Refusing to persist a Fly open-litellm URL as a harness remote. "
                "Hermes/OMB/Rakazo are LAN harnesses; LAN LLM is http://10.0.0.30:8000/v1."
            )
        entry["base_url"] = normalized
    if api_key is not None:
        entry["api_key"] = api_key
    if ui_url is not None:
        entry["ui_url"] = _normalize_base_url(ui_url) if ui_url else ""
    if cookie is not None:
        entry["cookie"] = cookie
    remotes[rid] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=4) + "\n", encoding="utf-8")
    logger.info("Persisted remotes.%s to %s", rid, path)
    return load_remote(rid, cfg), path


def _auth_headers(spec: RemoteSpec) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "open-swarm-remotes/1"}
    if spec.api_key:
        headers["Authorization"] = f"Bearer {spec.api_key}"
        headers["X-API-Key"] = spec.api_key
    if spec.cookie:
        headers["Cookie"] = spec.cookie
    return headers


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: Any = None,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> HttpResult:
    """One-shot HTTP. Never raises for network/HTTP; never retries."""
    started = time.monotonic()
    req_headers = dict(headers or {})
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            parsed: Any = None
            if text.strip():
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
            return HttpResult(
                status=getattr(resp, "status", None) or resp.getcode(),
                body=parsed,
                text=text,
                url=url,
                latency_ms=round((time.monotonic() - started) * 1000),
                headers={k.lower(): v for k, v in resp.headers.items()},
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        text = raw.decode("utf-8", errors="replace") if raw else ""
        parsed = None
        if text.strip():
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
        return HttpResult(
            status=exc.code,
            body=parsed,
            text=text,
            error=f"http {exc.code}",
            url=url,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return HttpResult(
            status=None,
            error=f"{type(exc).__name__}: {exc}",
            url=url,
            latency_ms=round((time.monotonic() - started) * 1000),
        )


def _tcp_probe(host: str, port: int, timeout: float) -> float | None:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return round((time.monotonic() - started) * 1000)
    except OSError:
        return None


def _extract_version(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in ("version", "app", "status", "runtime", "pid", "data", "ok"):
            if key in payload:
                if key == "data" and isinstance(payload[key], list):
                    return {"models": [m.get("id") for m in payload[key] if isinstance(m, dict)][:8]}
                return {key: payload[key]}
        return {k: payload[k] for k in list(payload)[:6]}
    if payload is not None:
        return payload
    return None


def check_health(remote_id: str, *, config: dict[str, Any] | None = None, timeout: float = _DEFAULT_TIMEOUT_S) -> HealthResult:
    """Honest health/version. One attempt. Never raises."""
    try:
        spec = load_remote(remote_id, config)
    except RemoteError as exc:
        return HealthResult(remote=remote_id, ok=False, state="UNKNOWN", detail=str(exc))

    if not spec.base_url:
        return HealthResult(remote=spec.id, ok=False, state="UNKNOWN", detail="base_url is empty")
    if _looks_like_forbidden_llm_proxy(spec.base_url):
        return HealthResult(
            remote=spec.id,
            ok=False,
            state="UNKNOWN",
            detail="base_url looks like Fly open-litellm — refuse to probe as a harness remote",
            url=spec.base_url,
        )

    host, port = spec.origin()
    if not host or not port:
        return HealthResult(remote=spec.id, ok=False, state="UNKNOWN", detail="unparseable base_url", url=spec.base_url)

    tcp_ms = _tcp_probe(host, port, timeout)
    if tcp_ms is None:
        return HealthResult(
            remote=spec.id,
            ok=False,
            state="DOWN",
            detail=f"tcp {host}:{port} refused/timed out",
            url=spec.base_url,
        )

    health_url = f"{spec.base_url}{spec.health_path}"
    result = http_json("GET", health_url, headers=_auth_headers(spec), timeout=timeout)
    version = _extract_version(result.body)

    if result.status in _UP:
        # Cheap extra version probe when health has no useful body.
        if version is None and spec.version_path != spec.health_path:
            extra = http_json(
                "GET",
                f"{spec.base_url}{spec.version_path}",
                headers=_auth_headers(spec),
                timeout=timeout,
            )
            if extra.status in _UP:
                version = _extract_version(extra.body) or extra.body
            elif extra.status in _AUTH:
                version = {"auth_required": True, "path": spec.version_path}
        return HealthResult(
            remote=spec.id,
            ok=True,
            state="UP",
            detail=f"tcp {tcp_ms}ms · http {result.status} on {spec.health_path}",
            http_status=result.status,
            version=version,
            latency_ms=result.latency_ms,
            url=health_url,
        )
    if result.status in _AUTH:
        return HealthResult(
            remote=spec.id,
            ok=True,
            state="UP",
            detail=f"tcp {tcp_ms}ms · http {result.status} (auth required — endpoint is alive)",
            http_status=result.status,
            version=version or {"auth_required": True},
            latency_ms=result.latency_ms,
            url=health_url,
        )
    if result.status is not None:
        return HealthResult(
            remote=spec.id,
            ok=False,
            state="DEGRADED",
            detail=f"tcp {tcp_ms}ms · http {result.status} on {spec.health_path}",
            http_status=result.status,
            version=version,
            latency_ms=result.latency_ms,
            url=health_url,
        )
    return HealthResult(
        remote=spec.id,
        ok=False,
        state="DEGRADED",
        detail=f"tcp {tcp_ms}ms · http probe failed: {result.error or 'no response'}",
        latency_ms=result.latency_ms,
        url=health_url,
    )


def check_all_health(*, config: dict[str, Any] | None = None, timeout: float = _DEFAULT_TIMEOUT_S) -> list[HealthResult]:
    return [check_health(rid, config=config, timeout=timeout) for rid in REMOTE_IDS]


def _hermes_list(spec: RemoteSpec, timeout: float) -> OperateResult:
    headers = _auth_headers(spec)
    models = http_json("GET", f"{spec.base_url}/v1/models", headers=headers, timeout=timeout)
    sessions = http_json("GET", f"{spec.base_url}/api/sessions", headers=headers, timeout=timeout)
    jobs = http_json("GET", f"{spec.base_url}/api/jobs", headers=headers, timeout=timeout)
    data: dict[str, Any] = {"models": models.body, "sessions": sessions.body, "jobs": jobs.body}
    statuses = [models.status, sessions.status, jobs.status]
    if any(s in _UP for s in statuses):
        return OperateResult(
            remote="hermes",
            op="list",
            ok=True,
            detail="listed Hermes models/sessions/jobs (missing slices stay null)",
            http_status=next((s for s in statuses if s in _UP), None),
            data=data,
        )
    if any(s in _AUTH for s in statuses):
        return OperateResult(
            remote="hermes",
            op="list",
            ok=False,
            detail="Hermes list endpoints require API_SERVER_KEY (Bearer). Set remotes.hermes.api_key or HERMES_API_KEY.",
            http_status=401,
            data=data,
        )
    return OperateResult(
        remote="hermes",
        op="list",
        ok=False,
        detail=models.error or sessions.error or jobs.error or "Hermes list failed",
        http_status=models.status,
        data=data,
    )


def _hermes_send(spec: RemoteSpec, prompt: str, timeout: float) -> OperateResult:
    if not prompt.strip():
        return OperateResult(remote="hermes", op="send", ok=False, detail="prompt is required")
    headers = _auth_headers(spec)
    result = http_json(
        "POST",
        f"{spec.base_url}/v1/runs",
        headers=headers,
        body={"input": prompt},
        timeout=timeout,
    )
    if result.status in _UP or result.status == 202:
        return OperateResult(
            remote="hermes",
            op="send",
            ok=True,
            detail="started Hermes run via POST /v1/runs",
            http_status=result.status,
            data=result.body or result.text,
        )
    if result.status in _AUTH:
        return OperateResult(
            remote="hermes",
            op="send",
            ok=False,
            detail="Hermes POST /v1/runs requires Bearer API_SERVER_KEY",
            http_status=result.status,
            data=result.body,
        )
    return OperateResult(
        remote="hermes",
        op="send",
        ok=False,
        detail=result.error or f"Hermes send failed (http {result.status})",
        http_status=result.status,
        data=result.body or result.text,
    )


def _omb_list(spec: RemoteSpec, timeout: float) -> OperateResult:
    result = http_json("GET", f"{spec.base_url}/api/bots", headers=_auth_headers(spec), timeout=timeout)
    if result.status in _UP:
        bots = result.body.get("bots") if isinstance(result.body, dict) else result.body
        count = len(bots) if isinstance(bots, list) else "?"
        return OperateResult(
            remote="omb",
            op="list",
            ok=True,
            detail=f"OpenMausBot listed {count} bot(s) via GET /api/bots",
            http_status=result.status,
            data=result.body,
        )
    if result.status in _AUTH:
        return OperateResult(
            remote="omb",
            op="list",
            ok=False,
            detail="OMB /api/bots requires auth. Set remotes.omb.api_key or OMB_API_KEY.",
            http_status=result.status,
            data=result.body,
        )
    return OperateResult(
        remote="omb",
        op="list",
        ok=False,
        detail=result.error or f"OMB list failed (http {result.status})",
        http_status=result.status,
        data=result.body or result.text,
    )


def _omb_send(spec: RemoteSpec, prompt: str, target: str, timeout: float) -> OperateResult:
    if not prompt.strip():
        return OperateResult(remote="omb", op="send", ok=False, detail="prompt is required")
    bot_id = (target or "").strip()
    headers = _auth_headers(spec)
    if not bot_id:
        listed = _omb_list(spec, timeout)
        bots = []
        if listed.ok and isinstance(listed.data, dict):
            bots = listed.data.get("bots") or []
        if isinstance(bots, list) and bots:
            first = bots[0] if isinstance(bots[0], dict) else {}
            bot_id = str(first.get("id") or "")
        if not bot_id:
            created = http_json("POST", f"{spec.base_url}/api/bots", headers=headers, body={}, timeout=timeout)
            if created.status in _UP and isinstance(created.body, dict):
                bot = created.body.get("bot") or {}
                bot_id = str(bot.get("id") or "")
            if not bot_id:
                return OperateResult(
                    remote="omb",
                    op="send",
                    ok=False,
                    detail="No OMB bot id given and none could be listed/created",
                    http_status=created.status if "created" in locals() else listed.http_status,
                    data={"list": listed.data},
                )
    result = http_json(
        "POST",
        f"{spec.base_url}/api/bots/{bot_id}/messages",
        headers=headers,
        body={"text": prompt},
        timeout=timeout,
    )
    if result.status in _UP or result.status == 202:
        return OperateResult(
            remote="omb",
            op="send",
            ok=True,
            detail=f"started OMB turn via POST /api/bots/{bot_id}/messages",
            http_status=result.status,
            data={"bot_id": bot_id, "response": result.body or result.text},
        )
    return OperateResult(
        remote="omb",
        op="send",
        ok=False,
        detail=result.error or f"OMB send failed (http {result.status})",
        http_status=result.status,
        data=result.body or result.text,
    )


def _rakazo_rpc(spec: RemoteSpec, path: str, payload: dict[str, Any], timeout: float) -> HttpResult:
    url = f"{spec.base_url}{path}"
    headers = _auth_headers(spec)
    # oRPC envelope used by the mobile probe and Hono RPCHandler.
    return http_json("POST", url, headers=headers, body={"json": payload}, timeout=timeout)


def _rakazo_list(spec: RemoteSpec, timeout: float) -> OperateResult:
    result = _rakazo_rpc(spec, "/rpc/bots/list", {}, timeout)
    if result.status in _UP:
        bots = result.body.get("json") if isinstance(result.body, dict) else result.body
        count = len(bots) if isinstance(bots, list) else "?"
        return OperateResult(
            remote="rakazo",
            op="list",
            ok=True,
            detail=f"Rakazo listed {count} bot(s) via POST /rpc/bots/list",
            http_status=result.status,
            data=result.body,
        )
    if result.status in _AUTH:
        return OperateResult(
            remote="rakazo",
            op="list",
            ok=False,
            detail=(
                "Rakazo /rpc/bots/list requires a Better Auth session. "
                "Health (GET /health) is public; operate is not. "
                "Set remotes.rakazo.cookie (or RAKAZO_SESSION_COOKIE) from a signed-in UI session, "
                "or a bearer if this deploy added API-key auth."
            ),
            http_status=result.status,
            data=result.body,
            gap="rakazo_rpc_requires_better_auth_session",
        )
    return OperateResult(
        remote="rakazo",
        op="list",
        ok=False,
        detail=result.error or f"Rakazo list failed (http {result.status})",
        http_status=result.status,
        data=result.body or result.text,
        gap="rakazo_rpc_unusable" if result.status is None else "",
    )


def _rakazo_send(spec: RemoteSpec, prompt: str, target: str, timeout: float) -> OperateResult:
    if not prompt.strip():
        return OperateResult(remote="rakazo", op="send", ok=False, detail="prompt is required")
    bot_id = (target or "").strip()
    if not bot_id:
        listed = _rakazo_list(spec, timeout)
        if not listed.ok:
            return OperateResult(
                remote="rakazo",
                op="send",
                ok=False,
                detail="Need a Rakazo botId (or a working list). " + listed.detail,
                http_status=listed.http_status,
                data=listed.data,
                gap=listed.gap,
            )
        bots = listed.data.get("json") if isinstance(listed.data, dict) else listed.data
        if isinstance(bots, list) and bots and isinstance(bots[0], dict):
            bot_id = str(bots[0].get("id") or "")
        if not bot_id:
            return OperateResult(
                remote="rakazo",
                op="send",
                ok=False,
                detail="Rakazo list returned no bot id; pass target=botId",
                data=listed.data,
            )
    result = _rakazo_rpc(
        spec,
        "/rpc/threads/send",
        {"botId": bot_id, "text": prompt},
        timeout,
    )
    if result.status in _UP:
        return OperateResult(
            remote="rakazo",
            op="send",
            ok=True,
            detail=f"sent Rakazo thread via POST /rpc/threads/send (bot {bot_id})",
            http_status=result.status,
            data=result.body,
        )
    if result.status in _AUTH:
        return OperateResult(
            remote="rakazo",
            op="send",
            ok=False,
            detail="Rakazo /rpc/threads/send requires Better Auth. Health still works without it.",
            http_status=result.status,
            data=result.body,
            gap="rakazo_rpc_requires_better_auth_session",
        )
    return OperateResult(
        remote="rakazo",
        op="send",
        ok=False,
        detail=result.error or f"Rakazo send failed (http {result.status})",
        http_status=result.status,
        data=result.body or result.text,
    )


def operate(
    remote_id: str,
    op: str,
    *,
    prompt: str = "",
    target: str = "",
    config: dict[str, Any] | None = None,
    timeout: float = _OPERATE_TIMEOUT_S,
) -> OperateResult:
    """List or send a job. Never raises; never crash-loops."""
    try:
        spec = load_remote(remote_id, config)
        rid = spec.id
        action = (op or "list").strip().lower()
        if action in ("start", "job", "run"):
            action = "send"
        if action not in ("list", "send"):
            return OperateResult(remote=rid, op=action, ok=False, detail=f"Unknown op '{op}'. Use list or send.")
        if not spec.base_url:
            return OperateResult(remote=rid, op=action, ok=False, detail="base_url is empty")
        if _looks_like_forbidden_llm_proxy(spec.base_url):
            return OperateResult(
                remote=rid,
                op=action,
                ok=False,
                detail="Refusing to operate against a Fly open-litellm URL",
            )
        if rid == "hermes":
            return _hermes_list(spec, timeout) if action == "list" else _hermes_send(spec, prompt, timeout)
        if rid == "omb":
            return _omb_list(spec, timeout) if action == "list" else _omb_send(spec, prompt, target, timeout)
        return _rakazo_list(spec, timeout) if action == "list" else _rakazo_send(spec, prompt, target, timeout)
    except Exception as exc:  # never let operate take down the process
        logger.warning("remotes.operate failed for %s %s: %s", remote_id, op, exc)
        return OperateResult(
            remote=str(remote_id),
            op=str(op),
            ok=False,
            detail=f"operate error: {exc}",
        )
