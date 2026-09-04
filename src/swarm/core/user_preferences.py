"""Registry + get/set helpers for per-user UI preferences (REQ-144).

Known first-class keys live in ``PREF_REGISTRY``. Extra keys may be stored in
the same JSON bag later without a migration. Secret-shaped keys are rejected.
"""

from __future__ import annotations

from typing import Any

from swarm.auth import request_principal, token_principal

# First-class rail chrome. More knobs (theme, …) can join this registry
# without a new table — they persist in UserPreference.values.
PREF_REGISTRY: dict[str, dict[str, str]] = {
    "favourites": {
        "type": "pin_list",
        "description": "Ordered favourite tiles (id + display name).",
    },
    "hidden_agents": {
        "type": "id_list",
        "description": "Hidden rail / Hidden Bots agent ids.",
    },
}

SECRET_KEY_FRAGMENTS = (
    "secret",
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "credential",
    "private_key",
)

FAVOURITES_KEY = "favourites"
HIDDEN_KEY = "hidden_agents"


def is_secret_key(name: str) -> bool:
    lowered = (name or "").strip().lower()
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def preference_identity(request) -> tuple[object | None, str, bool]:
    """Return ``(user_or_None, principal, is_guest)`` for this request.

    Logged-in Django user (including ``swarm-anon-preview``) → ``user:<name>``.
    Bearer / X-API-Key → ``token:<hash>``.
    Otherwise a Django session principal (guest). A session is minted if needed
    so the same browser can round-trip GET then PATCH.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user, f"user:{user.get_username()}", False

    principal = request_principal(request)
    if principal:
        return None, principal, False

    session = getattr(request, "session", None)
    if session is not None:
        if not session.session_key:
            session.save()
        if session.session_key:
            return None, f"session:{session.session_key}", True

    # Last resort (no session middleware). Still not a global singleton:
    # token_principal of empty is unused; isolate as anonymous-unsessioned.
    return None, "session:anonymous", True


def normalize_favourite(value: Any) -> dict[str, str] | None:
    if isinstance(value, str) and value.strip():
        ident = value.strip()
        return {"id": ident, "name": ident}
    if not isinstance(value, dict):
        return None
    ident = value.get("id")
    if not isinstance(ident, str) or not ident.strip():
        return None
    ident = ident.strip()
    name = value.get("name")
    label = name.strip() if isinstance(name, str) and name.strip() else ident
    return {"id": ident, "name": label}


def normalize_favourites(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    pins: list[dict[str, str]] = []
    for item in raw:
        pin = normalize_favourite(item)
        if pin is None or pin["id"] in seen:
            continue
        seen.add(pin["id"])
        pins.append(pin)
    return pins


def normalize_id_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    ids: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            continue
        ident = item.strip()
        if ident in seen:
            continue
        seen.add(ident)
        ids.append(ident)
    return ids


def empty_values() -> dict[str, Any]:
    return {FAVOURITES_KEY: [], HIDDEN_KEY: []}


def coerce_values(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return empty_values()
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key or is_secret_key(key):
            continue
        if key == FAVOURITES_KEY:
            out[key] = normalize_favourites(value)
        elif key == HIDDEN_KEY:
            out[key] = normalize_id_list(value)
        else:
            out[key] = value
    out.setdefault(FAVOURITES_KEY, [])
    out.setdefault(HIDDEN_KEY, [])
    return out


def merge_values(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = coerce_values(current)
    incoming = patch if isinstance(patch, dict) else {}
    for key, value in incoming.items():
        if not isinstance(key, str) or not key or is_secret_key(key):
            continue
        if key == FAVOURITES_KEY:
            merged[key] = normalize_favourites(value)
        elif key == HIDDEN_KEY:
            merged[key] = normalize_id_list(value)
        else:
            merged[key] = value
    return merged


def extras_bag(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if key not in PREF_REGISTRY
    }


def public_payload(
    *,
    principal: str,
    guest: bool,
    empty: bool,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bag = coerce_values(values or {})
    return {
        "object": "user_preferences",
        "principal": principal,
        "guest": guest,
        "empty": empty,
        "favourites": bag[FAVOURITES_KEY],
        "hidden_agents": bag[HIDDEN_KEY],
        "values": extras_bag(bag),
        "registry": [
            {"key": key, **meta} for key, meta in PREF_REGISTRY.items()
        ],
    }


# Re-export so views can stamp token principals without importing auth twice.
__all__ = [
    "FAVOURITES_KEY",
    "HIDDEN_KEY",
    "PREF_REGISTRY",
    "coerce_values",
    "empty_values",
    "extras_bag",
    "is_secret_key",
    "merge_values",
    "normalize_favourites",
    "normalize_id_list",
    "preference_identity",
    "public_payload",
    "token_principal",
]
