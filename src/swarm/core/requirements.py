import os
import re
from typing import Any, Dict, List, Tuple

from .config_loader import load_full_configuration


UNRESOLVED_VAR_PATTERN_1 = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
UNRESOLVED_VAR_PATTERN_2 = re.compile(r"(?<!\$)\$([A-Za-z_][A-Za-z0-9_]*)")


def _find_unresolved_envs(value: Any) -> List[str]:
    """Return env var names that appear unresolved in a string value."""
    if not isinstance(value, str):
        return []
    names = set(UNRESOLVED_VAR_PATTERN_1.findall(value))
    names.update(UNRESOLVED_VAR_PATTERN_2.findall(value))
    return sorted(names)


def load_active_config() -> Dict[str, Any]:
    """Load the active configuration using the standard loader.

    Uses a dummy blueprint name to avoid merging per-blueprint overrides.
    """
    return load_full_configuration(blueprint_class_name="__requirements__")


def evaluate_mcp_compliance(
    required_servers: List[str] | None,
    mcp_config: Dict[str, Any],
    *,
    blueprint_env_vars: List[str] | None = None,
) -> Dict[str, Any]:
    """Compare required MCP servers against the current mcpServers config.

    Returns a dict including status, missing servers, per-server details,
    and any missing blueprint-level env vars.
    """
    req = required_servers or []
    bp_env = blueprint_env_vars or []

    server_details: Dict[str, Dict[str, Any]] = {}
    missing_servers: List[str] = []

    for name in req:
        entry = mcp_config.get(name)
        present = entry is not None
        has_command = bool(entry.get("command")) if present else False
        has_args = bool(entry.get("args")) if present else False
        unresolved_env: List[str] = []

        if present:
            env_dict = entry.get("env", {}) if isinstance(entry, dict) else {}
            # Check unresolved env placeholders in values
            for v in env_dict.values():
                unresolved_env.extend(_find_unresolved_envs(v))
        else:
            missing_servers.append(name)

        server_details[name] = {
            "present": present,
            "has_command": has_command,
            "has_args": has_args,
            "unresolved_env": sorted(set(unresolved_env)),
        }

    # Blueprint-level env var presence (in OS env)
    missing_bp_env: List[str] = [e for e in bp_env if not os.environ.get(e)]

    status = "ok"
    if missing_servers:
        status = "missing"
    elif any(d.get("unresolved_env") for d in server_details.values()) or missing_bp_env:
        status = "partial"

    # Aggregate unresolved envs across servers for convenience
    aggregated_unresolved = sorted({x for d in server_details.values() for x in d.get("unresolved_env", [])})

    return {
        "status": status,
        "required": req,
        "missing_servers": missing_servers,
        "server_details": server_details,
        "blueprint_env_missing": missing_bp_env,
        "unresolved_env": aggregated_unresolved,
    }

