"""Built-in catalog of known-good CLI adapter configs.

Starting-point ``cli_agents`` configs for popular agentic CLIs. Lets
``swarm-cli cli-agents --suggest`` propose a ready-to-paste config block for any
supported CLI that is installed on the host but not yet in the user's swarm
config.

Each entry runs the CLI **one-shot, non-interactive, auto-approve** (full
capability) — the flag that matters is the auto-approve one, without which the
CLI blocks on a permission prompt and is killed on timeout (see
``docs/CLI_FUSION.md``). That is how Open Swarm **simulates always-approve**;
Agent Router Shift+Tab therefore cycles only plan / auto-edit / default.
Exact flags and JSON shapes drift by CLI version, so these are suggestions
to verify with each CLI's ``--help``, not guarantees.

Known per-CLI gotchas are encoded here so the defaults *just run* (verified live
2026-06-16):

* **gemini** refuses to run in an "untrusted" directory — ``--skip-trust`` (or
  ``GEMINI_CLI_TRUST_WORKSPACE=true``) is required for non-interactive use.
* **opencode** has no usable default model in ``run`` mode (its built-in default
  errors as "not supported"), so an explicit ``--model`` is required. The value
  below is account/version-specific — run ``opencode models`` to pick one.
* **agy** treats ``-p`` / ``--print`` as a flag that *consumes the next argv
  token as the prompt*. ``agy -p --output-format json 'hi'`` errors with
  ``-p took "--output-format" as its prompt``. Attach the prompt to the flag
  (``-p={prompt}``) and keep ``--output-format`` as a sibling flag.

The gemini default uses the fast flash tier (no ``-m``). To select the pro tier
use ``with_model("gemini", "gemini-3-pro-preview", timeout=600)`` — but note
that on the free ``oauth-personal`` login the pro model is heavily throttled and
can take minutes (or stall) even on a one-word prompt; it is far more usable on a
paid ``GEMINI_API_KEY``. Flash answers in a few seconds.
"""

from __future__ import annotations

import shutil
from typing import Any

# name -> adapter config dict (same shape as one `cli_agents` entry).
CATALOG: dict[str, dict[str, Any]] = {
    "grok": {
        # xAI's grok CLI (also installed as `agent`). -p/--single is the
        # non-interactive print mode; --always-approve auto-approves tool use.
        # Flags before -p so later argv cannot be swallowed as the prompt.
        # Inherits the full env (auth is file-based, not a single known var).
        "cmd": ["grok", "--output-format", "json", "--always-approve", "-p", "{prompt}"],
        "parse": "json:.text",
        "mode": "write",
        "timeout": 240,
    },
    "agy": {
        # Agy print-mode: -p/--print consumes the next argv token as the
        # prompt, so the prompt MUST be attached (-p={prompt}), not a
        # following positional. JSON shape is {response, status, ...}.
        "cmd": [
            "agy",
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
            "-p={prompt}",
        ],
        "parse": "json:.response",
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
    "pi": {
        # pi -p/--print is non-interactive; prompt is a positional message
        # (not attached to -p). --mode text; --no-session keeps verify runs
        # ephemeral. --approve trusts project-local files for that run.
        "cmd": ["pi", "-p", "--mode", "text", "--no-session", "--approve", "{prompt}"],
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


# How each catalogued CLI names and resumes a session. First-turn ``cmd`` stays
# one-shot; Swarm inserts ``resume_argv`` only when a stored id exists.
# ``{session_id}`` is replaced with the stored id. Distinct from Django/API
# conversation ids and from OS ``start_new_session`` (process-group kill).
#
# antigravity is **not** in CATALOG (not wired). If it is added later, headless
# resume is ``agy -p --conversation <id>`` (JSON often includes conversation_id).
SESSION: dict[str, dict[str, Any]] = {
    "grok": {
        "resume_argv": ["--resume", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".sessionId", ".session_id"],
        "notes": (
            "grok -p --resume <uuid> (also -r). --session-id / -s names a NEW "
            "session; do not use it to resume. JSON often includes sessionId."
        ),
    },
    "claude": {
        "resume_argv": ["--resume", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".session_id"],
        "notes": (
            "claude -p --resume <uuid> (also -r). JSON result includes session_id "
            "even when parse is json:.result. A resume may mint a new session_id; "
            "store the latest. --session-id names a new session, not a resume."
        ),
    },
    "gemini": {
        "resume_argv": ["--resume", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".session_id", ".sessionId"],
        "notes": (
            "gemini -p --resume <uuid> (also -r). --session-id starts a NEW "
            "session and conflicts with --resume. Capture id from JSON when present."
        ),
    },
    "codex": {
        "resume_argv": ["resume", "{session_id}"],
        "resume_insert": 2,  # after `codex exec` → `codex exec resume <id> …`
        "session_id_paths": [".thread_id", ".session_id"],
        "notes": (
            "codex exec resume <SESSION_ID> <prompt> (subcommand, not a --flag). "
            "Default catalog parse is text; thread_id appears when --json is used. "
            "Interactive `codex resume` is a TUI — do not use it here."
        ),
    },
    "opencode": {
        "resume_argv": ["--session", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".session", ".sessionID", ".id"],
        "notes": (
            "opencode run --session <id> (also -s). --continue/-c is last-session "
            "in the cwd, not thread-scoped — do not use it. Capture id when the "
            "CLI emits JSON; the default catalog parse is text."
        ),
    },
    "agy": {
        "resume_argv": ["--conversation", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".conversation_id", ".conversationId"],
        "notes": (
            "agy -p --conversation <id>. --continue is most-recent, not "
            "thread-scoped — do not use it here."
        ),
    },
    "pi": {
        "resume_argv": ["--session", "{session_id}"],
        "resume_insert": 1,
        "session_id_paths": [".session", ".id"],
        "notes": (
            "pi -p --session <path|id>. --resume/-r is a TUI picker; "
            "--continue/-c is last session — do not use those here. "
            "Catalog verify runs use --no-session (ephemeral)."
        ),
    },
}


# Default capability traits (0..1) per known CLI for inference-profile matching
# (see swarm.core.inference_profile). These are sensible starting points the
# USER is expected to tune for their own plans/models via a per-agent ``traits``
# block in config — e.g. someone on a top grok plan may rate it 1.0 intelligence.
# cost = cheapness (1.0 = cheapest). gemini defaults to its fast/cheap flash tier.
CLI_TRAITS: dict[str, dict[str, float]] = {
    "grok":     {"intelligence": 0.90, "speed": 0.60, "cost": 0.55},
    "agy":      {"intelligence": 0.85, "speed": 0.65, "cost": 0.50},
    "claude":   {"intelligence": 0.95, "speed": 0.55, "cost": 0.35},
    "gemini":   {"intelligence": 0.60, "speed": 0.92, "cost": 0.90},
    "codex":    {"intelligence": 0.75, "speed": 0.60, "cost": 0.50},
    "opencode": {"intelligence": 0.55, "speed": 0.65, "cost": 0.75},
    "pi":       {"intelligence": 0.70, "speed": 0.70, "cost": 0.70},
}

# First-class sidebar CLIs — always listed like remote FRAMEWORKS (OpenMausBot),
# even when the designer has not created a `kind=cli` record. Other catalog
# CLIs stay available in the backend picker / designer.
# Grok rail verify rows use ``{name}_agent`` ids (grok_agent, agy_agent, …).
SIDEBAR_CLIS: tuple[str, ...] = ("grok", "agy", "opencode", "pi")

CLI_SIDEBAR: dict[str, dict[str, str]] = {
    "grok": {
        "name": "Grok",
        "specialty": "xAI Grok CLI",
        "description": "Host grok CLI in one-shot print mode (--always-approve).",
        "color": "#22c55e",
        "icon": "⚡",
    },
    "agy": {
        "name": "Agy",
        "specialty": "Agy CLI",
        "description": "Host agy CLI in one-shot print mode (auto-approve tools).",
        "color": "#38bdf8",
        "icon": "🛠️",
    },
    "opencode": {
        "name": "OpenCode",
        "specialty": "OpenCode CLI",
        "description": "Host opencode CLI one-shot (run + explicit --model).",
        "color": "#a78bfa",
        "icon": "⌨️",
    },
    "pi": {
        "name": "Pi",
        "specialty": "Pi CLI",
        "description": "Host pi CLI in non-interactive print mode (-p).",
        "color": "#fb923c",
        "icon": "π",
    },
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
    "agy": "--model",      # agy --model <name>
    "grok": "-m",          # grok -m/--model <id> (verified: grok-4.6, grok-4.5)
}

# Suggested model ids for the Agent Router CLI-model dropdown. The UI always
# offers a custom string on top of these; they are starting points, not a
# live catalog from the host CLI.
CLI_MODELS: dict[str, list[str]] = {
    "grok": ["grok-4.6", "grok-4.5"],
    "agy": [
        "gemini-3.8-flash-high",
        "gemini-3.8-flash-medium",
        "gemini-3.1-pro-high",
        "claude-sonnet-4-6",
        "claude-opus-4-6-thinking",
        "gpt-oss-120b-medium",
    ],
    "gemini": ["gemini-3-flash-preview", "gemini-3-pro-preview"],
    "claude": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
    "opencode": ["opencode/big-pickle"],
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


def listed_cli_specs() -> list[dict[str, Any]]:
    """Host grok/agy as Agent Router sidebar specs (OpenMausBot-style).

    Always returned so the sidebar does not require a designer POST. A later
    ``kind=cli`` design with the same ``agent_id`` may overlay these.
    """
    specs: list[dict[str, Any]] = []
    for name in SIDEBAR_CLIS:
        if name not in CATALOG:
            continue
        meta = CLI_SIDEBAR.get(name) or {}
        specs.append({
            "agent_id": name,
            "name": meta.get("name") or name.title(),
            "kind": "cli",
            "agent_type": "cli",
            "cli": name,
            "specialty": meta.get("specialty") or f"{name} CLI",
            "description": meta.get("description") or f"Host {name} CLI, one-shot print mode.",
            "color": meta.get("color") or "#6366f1",
            "icon": meta.get("icon") or "⌨️",
            "group": "tools",
            "type": "specialist",
        })
    return specs


def rail_cli_agent_id(cli_name: str) -> str:
    """Grok-rail id: grok → grok_agent."""
    return f"{cli_name}_agent"


def cli_from_rail_id(agent_id: str | None) -> str | None:
    """Map grok_agent / grok → catalog CLI name, or None."""
    raw = str(agent_id or "").strip().lower()
    if not raw:
        return None
    if raw.endswith("_agent"):
        raw = raw[: -len("_agent")]
    if raw in CATALOG:
        return raw
    return None


def rail_cli_rows() -> list[dict[str, Any]]:
    """Rows for the Grok conversation rail (id ``grok_agent``, …)."""
    rows: list[dict[str, Any]] = []
    for spec in listed_cli_specs():
        name = str(spec.get("cli") or spec.get("agent_id") or "")
        if not name:
            continue
        meta = CLI_SIDEBAR.get(name) or {}
        rows.append({
            "id": rail_cli_agent_id(name),
            "object": "cli.agent",
            "name": rail_cli_agent_id(name),
            "cli": name,
            "kind": "cli",
            "description": meta.get("description") or spec.get("description") or f"{name} CLI",
            "installed": bool(shutil.which(CATALOG[name]["cmd"][0])),
        })
    return rows


def session_policy(name: str) -> dict[str, Any] | None:
    """How ``name`` names and resumes a CLI session, or None if undocumented."""
    entry = SESSION.get(name)
    return _deepcopy(entry) if entry is not None else None


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
