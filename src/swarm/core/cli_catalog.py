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
"""

from __future__ import annotations

import shutil
from typing import Any

# name -> adapter config dict (same shape as one `cli_agents` entry).
CATALOG: dict[str, dict[str, Any]] = {
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


def catalog_names() -> list[str]:
    """Names of every CLI the catalog knows about (sorted)."""
    return sorted(CATALOG)


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
