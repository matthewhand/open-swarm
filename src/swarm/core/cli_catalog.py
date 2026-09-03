"""Built-in catalog of known-good CLI adapter configs.

Starting-point ``cli_agents`` configs for popular agentic CLIs. Lets
``swarm-cli cli-agents --suggest`` propose a ready-to-paste config block for any
supported CLI that is installed on the host but not yet in the user's swarm
config.

Each entry runs the CLI **one-shot, non-interactive, auto-approve** (full
capability) — the flag that matters is the auto-approve one, without which the
CLI blocks on a permission prompt and is killed on timeout (see
``docs/CLI_FUSION.md``). Exact flags and JSON shapes drift by CLI version, so
these are suggestions to verify with each CLI's ``--help``, not guarantees.

Known per-CLI gotchas are encoded here so the defaults *just run* (verified live
2026-06-16):

* **gemini** refuses to run in an "untrusted" directory — ``--skip-trust`` (or
  ``GEMINI_CLI_TRUST_WORKSPACE=true``) is required for non-interactive use.
* **opencode** has no usable default model in ``run`` mode (its built-in default
  errors as "not supported"), so an explicit ``--model`` is required. The value
  below is account/version-specific — run ``opencode models`` to pick one.

The gemini default uses the fast flash tier (no ``-m``). To select the pro tier
use ``with_model("gemini", "gemini-3-pro-preview", timeout=600)`` — but note
that on the free ``oauth-personal`` login the pro model is heavily throttled and
can take minutes (or stall) even on a one-word prompt; it is far more usable on a
paid ``GEMINI_API_KEY``. Flash answers in a few seconds.
"""

from __future__ import annotations

import json
import re
import shutil
from typing import Any

# name -> adapter config dict (same shape as one `cli_agents` entry).
CATALOG: dict[str, dict[str, Any]] = {
    "grok": {
        # xAI's grok CLI (also installed as `agent`). -p/--single is the
        # non-interactive print mode; --always-approve auto-approves tool use.
        # Inherits the full env (auth is file-based, not a single known var).
        "cmd": ["grok", "-p", "{prompt}", "--output-format", "json", "--always-approve"],
        "parse": "json:.text",
        "mode": "write",
        "timeout": 240,
    },
    "claude": {
        "cmd": ["claude", "-p", "{prompt}", "--output-format", "json",
                "--dangerously-skip-permissions"],
        "parse": "json:.result",
        "mode": "write",
        "timeout": 240,
        "env_allowlist": ["ANTHROPIC_API_KEY"],
    },
    "gemini": {
        # --skip-trust: gemini refuses to run in an untrusted dir without it.
        "cmd": ["gemini", "-p", "{prompt}", "-o", "json", "--yolo", "--skip-trust"],
        "parse": "json:.response",
        "mode": "write",
        "timeout": 240,
        "env_allowlist": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    },
    "codex": {
        "cmd": ["codex", "exec", "{prompt}", "--dangerously-bypass-approvals-and-sandbox"],
        "parse": "text",
        "mode": "write",
        "timeout": 240,
        "env_allowlist": ["OPENAI_API_KEY"],
    },
    "opencode": {
        # --model: opencode's built-in default errors as "not supported"; an
        # explicit model is required. This value is account/version-specific —
        # run `opencode models` to pick one available to you.
        "cmd": ["opencode", "run", "{prompt}", "--model", "opencode/big-pickle"],
        "parse": "text",
        "mode": "write",
        "timeout": 240,
    },
}


# CLIs with a BUILT-IN "run N candidates and pick the best" mode (native
# consensus) — the CLI fans out internally in one call, distinct from the
# framework running it N times. Maps cli name -> argv to APPEND, with "{n}"
# substituted for the candidate count.
NATIVE_CONSENSUS: dict[str, list[str]] = {
    "grok": ["--best-of-n", "{n}"],  # verified live: grok runs an N-candidate tournament
}


# Token substituted into resume_argv when a stored CLI session id is replayed.
SESSION_ID_TOKEN = "{session_id}"

# How each CLI names / resumes a session it owns. Swarm stores the id next to
# the chat thread (REQ-52) and injects resume_argv on the next send.
# ``wired`` is False when the CLI is documented but not in CATALOG yet.
SESSION_RESUME: dict[str, dict[str, Any]] = {
    "grok": {
        "resume_argv": ["--resume", SESSION_ID_TOKEN],
        "id_paths": ["session_id", "sessionId"],
        "store": "~/.grok/sessions",
    },
    "claude": {
        "resume_argv": ["--resume", SESSION_ID_TOKEN],
        "id_paths": ["session_id"],
        "store": "claude session files (JSON session_id)",
    },
    "gemini": {
        "resume_argv": ["--resume", SESSION_ID_TOKEN],
        "id_paths": ["session_id", "sessionId"],
        "store": "gemini project sessions",
    },
    "codex": {
        # `codex exec resume <SESSION_ID> <prompt> …` — insert after `exec`.
        "resume_argv": ["resume", SESSION_ID_TOKEN],
        "resume_insert_after": "exec",
        "id_paths": ["session_id", "thread_id", "id"],
        "store": "codex session / rollout store",
    },
    "opencode": {
        "resume_argv": ["--session", SESSION_ID_TOKEN],
        "id_paths": ["sessionID", "session_id", "id"],
        "store": "opencode session store",
    },
    # Documented for when an adapter is wired; not a catalog entry today.
    "antigravity": {
        "resume_argv": ["--conversation", SESSION_ID_TOKEN],
        "id_paths": ["conversation_id", "session_id"],
        "store": "agy conversation id",
        "wired": False,
    },
}


# Default capability traits (0..1) per known CLI for inference-profile matching
# (see swarm.core.inference_profile). These are sensible starting points the
# USER is expected to tune for their own plans/models via a per-agent ``traits``
# block in config — e.g. someone on a top grok plan may rate it 1.0 intelligence.
# cost = cheapness (1.0 = cheapest). gemini defaults to its fast/cheap flash tier.
CLI_TRAITS: dict[str, dict[str, float]] = {
    "grok":     {"intelligence": 0.90, "speed": 0.60, "cost": 0.55},
    "claude":   {"intelligence": 0.95, "speed": 0.55, "cost": 0.35},
    "gemini":   {"intelligence": 0.60, "speed": 0.92, "cost": 0.90},
    "codex":    {"intelligence": 0.75, "speed": 0.60, "cost": 0.50},
    "opencode": {"intelligence": 0.55, "speed": 0.65, "cost": 0.75},
}


def cli_traits(name: str) -> dict[str, float] | None:
    """Default capability traits for a known CLI, or None if unknown."""
    t = CLI_TRAITS.get(name)
    return dict(t) if t is not None else None


def has_native_consensus(name: str) -> bool:
    """True when this CLI has a built-in consensus/heavy mode the catalog knows."""
    return name in NATIVE_CONSENSUS


def native_consensus_flags(name: str, n: int = 2) -> list[str] | None:
    """argv to append to enable ``name``'s built-in consensus for N candidates, or None."""
    tmpl = NATIVE_CONSENSUS.get(name)
    if not tmpl:
        return None
    count = str(max(2, int(n)))
    return [count if part == "{n}" else part for part in tmpl]


def with_native_consensus(name: str, n: int = 2) -> dict[str, Any] | None:
    """A catalog entry for ``name`` with its built-in consensus mode enabled.

    Returns None if the CLI is unknown or has no native consensus flag.
    """
    entry = catalog_entry(name)
    flags = native_consensus_flags(name, n)
    if entry is None or flags is None:
        return None
    entry["cmd"] = list(entry["cmd"]) + flags
    return entry


# Flag each CLI uses to pin a specific model, so callers can request a
# particular tier (e.g. gemini's pro vs. flash). Only flags verified against the
# installed CLI version belong here; omit a CLI rather than guess.
MODEL_FLAG: dict[str, str] = {
    "gemini": "-m",        # verified live (gemini 0.45): -m gemini-3-pro-preview
    "claude": "--model",   # claude -p --model <name>
    "opencode": "--model", # opencode run --model <name>
}


# Default capability traits (0..1) per known MODEL, keyed by model id. These
# refine the per-provider CLI_TRAITS default: a provider runs many models (e.g.
# gemini flash vs pro) with very different intelligence/speed/cost. Illustrative
# starting points — users override per-model via config. cost = cheapness.
MODEL_TRAITS: dict[str, dict[str, float]] = {
    "gemini-3-pro-preview":   {"intelligence": 0.92, "speed": 0.35, "cost": 0.30},
    "gemini-3-flash-preview": {"intelligence": 0.62, "speed": 0.95, "cost": 0.92},
    "claude-opus-4-8":        {"intelligence": 0.98, "speed": 0.45, "cost": 0.20},
    "claude-sonnet-4-6":      {"intelligence": 0.90, "speed": 0.70, "cost": 0.55},
    "claude-haiku-4-5":       {"intelligence": 0.70, "speed": 0.92, "cost": 0.85},
}


def model_traits(model: str) -> dict[str, float] | None:
    """Default capability traits for a known model id, or None if unknown."""
    t = MODEL_TRAITS.get(model)
    return dict(t) if t is not None else None


def apply_model(entry: dict[str, Any], name: str, model: str) -> dict[str, Any]:
    """Return a copy of ``entry`` with ``name``'s model flag set to ``model``.

    Replaces an already-pinned model (e.g. opencode's default) rather than
    duplicating it; a no-op for CLIs with no known model flag.
    """
    entry = _deepcopy(entry)
    flag = MODEL_FLAG.get(name)
    if flag is None:
        return entry
    cmd = list(entry.get("cmd") or [])
    if not cmd:
        return entry  # no command to pin a model on; don't fabricate a flag-only cmd
    if flag in cmd:
        i = cmd.index(flag)
        if i + 1 < len(cmd):
            cmd[i + 1] = model
        else:
            cmd.append(model)
    else:
        cmd += [flag, model]
    entry["cmd"] = cmd
    return entry


def with_model(name: str, model: str, *, timeout: int | None = None) -> dict[str, Any] | None:
    """A catalog entry for ``name`` pinned to a specific ``model``.

    Pro/heavy tiers (notably ``gemini-3-pro-preview``) think for much longer than
    the flash default, so pass a larger ``timeout`` when selecting one. Returns
    None for an unknown CLI; returns the entry unchanged if the catalog has no
    known model flag for it.
    """
    base = catalog_entry(name)
    if base is None:
        return None
    entry = apply_model(base, name, model)
    if timeout is not None:
        entry["timeout"] = timeout
    return entry


def catalog_names() -> list[str]:
    """Names of every CLI the catalog knows about (sorted)."""
    return sorted(CATALOG)


def installed_catalog_clis() -> list[str]:
    """Catalog CLIs whose executable resolves on this host (sorted)."""
    return [n for n in catalog_names() if shutil.which(CATALOG[n]["cmd"][0])]


def build_starter_config(installed: list[str] | None = None) -> dict[str, Any]:
    """A complete, ready-to-run swarm_config for the installed catalog CLIs.

    Wires every composition mode (cli_fusion / cli_orchestrator / cli_map) over
    whatever catalog CLIs are present. The single-agent default and the
    judge/router/reducer/planner roles prefer ``grok`` (then ``claude``, then the
    first available); the panels include *every* installed CLI, so the other
    agents are only engaged for the multi-agent paths. Includes a default ``llm``
    block so the config passes validation. When nothing is installed, returns
    just the llm + an empty ``cli_agents`` block.
    """
    if installed is None:
        installed = installed_catalog_clis()
    agents = {n: catalog_entry(n) for n in installed if n in CATALOG}
    names = sorted(agents)
    cfg: dict[str, Any] = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "${OPENAI_API_KEY}",
            }
        },
        "cli_agents": agents,
    }
    if names:
        primary = next((c for c in ("grok", "claude") if c in names), names[0])
        cfg["cli_fusion"] = {
            "default_cli": primary,
            "default_preset": "all",
            "show_analysis": True,
            "presets": {"all": {"panel": names, "judge": primary}},
        }
        cfg["cli_orchestrator"] = {"router": primary, "panel": names, "judge": primary}
        cfg["cli_map"] = {"planner": primary, "workers": names, "reducer": primary}
    return cfg


def catalog_entry(name: str) -> dict[str, Any] | None:
    """A copy of the catalog config for ``name`` (None if unknown)."""
    entry = CATALOG.get(name)
    return _deepcopy(entry) if entry is not None else None


def executable_for(name: str) -> str | None:
    """The executable (``cmd[0]``) a catalog entry runs, or None if unknown."""
    entry = CATALOG.get(name)
    return entry["cmd"][0] if entry else None


def suggest_unconfigured(
    configured_names: list[str] | None,
    *,
    installed_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Return ``{name: config}`` for catalog CLIs not already configured.

    Skips any name already present in ``configured_names``. When
    ``installed_only`` (default), also skips CLIs whose executable does not
    resolve on PATH — so suggestions are actionable on *this* host.
    """
    configured = set(configured_names or ())
    out: dict[str, dict[str, Any]] = {}
    for name, cfg in CATALOG.items():
        if name in configured:
            continue
        if installed_only and shutil.which(cfg["cmd"][0]) is None:
            continue
        out[name] = _deepcopy(cfg)
    return out


def _deepcopy(cfg: dict[str, Any]) -> dict[str, Any]:
    """Shallow structure with copied list/dict values (configs are 1 level deep)."""
    return {
        k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
        for k, v in cfg.items()
    }


# Session ids are opaque CLI handles, never credentials. Reject key-shaped values.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SECRETISH_RE = re.compile(r"(?i)(sk-|api[_-]?key|bearer\s|-----begin)")
_SESSION_JSON_KEY_RE = re.compile(
    r'"(?:session_id|sessionId|sessionID|conversation_id|thread_id)"\s*:\s*"([^"]+)"'
)
_DEFAULT_ID_PATHS = ("session_id", "sessionId", "sessionID", "conversation_id", "thread_id")


def session_resume_spec(name: str) -> dict[str, Any] | None:
    """Copy of the resume spec for ``name``, or None if unknown."""
    entry = SESSION_RESUME.get(name)
    if entry is None:
        return None
    out = dict(entry)
    if isinstance(out.get("resume_argv"), list):
        out["resume_argv"] = list(out["resume_argv"])
    if isinstance(out.get("id_paths"), list):
        out["id_paths"] = list(out["id_paths"])
    return out


def has_session_resume(name: str) -> bool:
    """True when Swarm can inject a resume flag for this CLI (wired + argv)."""
    spec = SESSION_RESUME.get(name)
    return bool(spec and spec.get("resume_argv") and spec.get("wired", True))


def normalize_cli_session_id(raw: Any) -> str | None:
    """Return a safe session id, or None if missing / secret-shaped / invalid."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or not _SESSION_ID_RE.match(text) or _SECRETISH_RE.search(text):
        return None
    return text


def extract_session_id(
    data: Any, *, name: str | None = None, paths: list[str] | None = None
) -> str | None:
    """Pull a session id out of parsed JSON (top-level, then one nested dict)."""
    keys: list[str] = []
    for key in (*(paths or ()), *(((session_resume_spec(name) or {}).get("id_paths")) or ()), *_DEFAULT_ID_PATHS):
        if key not in keys:
            keys.append(key)
    if isinstance(data, dict):
        for key in keys:
            sid = normalize_cli_session_id(data.get(key))
            if sid:
                return sid
        for value in data.values():
            if isinstance(value, dict):
                sid = extract_session_id(value, paths=keys)
                if sid:
                    return sid
    return None


def extract_session_id_from_text(
    text: str | None, *, name: str | None = None, paths: list[str] | None = None
) -> str | None:
    """Parse a session id from JSON / NDJSON stdout, or a quoted key in text."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if parsed is not None:
        sid = extract_session_id(parsed, name=name, paths=paths)
        if sid:
            return sid
    last: Any = None
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    if last is not None:
        sid = extract_session_id(last, name=name, paths=paths)
        if sid:
            return sid
    for match in _SESSION_JSON_KEY_RE.finditer(raw):
        sid = normalize_cli_session_id(match.group(1))
        if sid:
            return sid
    return None


def apply_session_id(
    cmd: list[str],
    name: str,
    session_id: str,
    *,
    resume_argv: list[str] | None = None,
    insert_after: str | None = None,
) -> list[str]:
    """Return ``cmd`` with this CLI's resume argv injected, or ``cmd`` unchanged."""
    sid = normalize_cli_session_id(session_id)
    spec = session_resume_spec(name) or {}
    tmpl = resume_argv if resume_argv is not None else spec.get("resume_argv")
    after = insert_after if insert_after is not None else spec.get("resume_insert_after")
    if not sid or not tmpl or spec.get("wired", True) is False and resume_argv is None:
        return list(cmd)
    extra = [sid if part == SESSION_ID_TOKEN else str(part) for part in tmpl]
    out = list(cmd)
    if after:
        try:
            idx = out.index(after)
            return out[: idx + 1] + extra + out[idx + 1 :]
        except ValueError:
            pass
    return out + extra
