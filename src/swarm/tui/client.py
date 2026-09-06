"""HTTP client for the Wave 0 TUI — same REST the SPA rail reads.

Does not talk to Herdr over SSH, does not hit ``:8001``, and does not invent
local agents when the API is down.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

# Compose / swarm-api default. Oracle / FF preview is :8001 — do not use it.
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
BASE_URL_ENV = "SWARM_API_BASE"
TOKEN_ENV_NAMES = ("API_AUTH_TOKEN", "SWARM_API_KEY")

GETTER = Callable[[str, dict[str, str]], httpx.Response]


class SwarmApiError(RuntimeError):
    """Honest API failure — never papered over with fake seats."""


@dataclass(frozen=True)
class RailSeat:
    """One AGENTS-rail row the TUI can show."""

    id: str
    name: str
    kind: str
    source: str


def resolve_base_url(explicit: str | None = None) -> str:
    """Prefer ``--base-url``, then ``SWARM_API_BASE``, then loopback :8000."""
    raw = (explicit or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).strip()
    return raw.rstrip("/")


def resolve_token() -> str | None:
    """Bearer from env. Docs name the variables; values stay out of the repo."""
    for key in TOKEN_ENV_NAMES:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def is_rail_seat(row: dict[str, Any]) -> bool:
    """Match ``webui/frontend/src/lib/railSeats.ts`` ``isRailSeat``."""
    kind = str(row.get("kind") or "").strip().lower()
    if kind in {"cli", "herdr", "api"}:
        return True
    return row.get("rail") is True


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _request(getter: GETTER, url: str, headers: dict[str, str]) -> httpx.Response:
    try:
        return getter(url, headers)
    except httpx.HTTPError as exc:
        raise SwarmApiError(f"API unreachable at {url}: {exc}") from exc


def _json_object(response: httpx.Response, url: str) -> dict[str, Any]:
    if response.status_code in {401, 403}:
        raise SwarmApiError(
            f"API auth failed ({response.status_code}) at {url}. "
            "Set API_AUTH_TOKEN or SWARM_API_KEY (env-var names only)."
        )
    if response.status_code >= 400:
        raise SwarmApiError(f"API error {response.status_code} at {url}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise SwarmApiError(f"API returned non-JSON at {url}") from exc
    if not isinstance(payload, dict):
        raise SwarmApiError(f"API returned a non-object at {url}")
    return payload


def _optional_json(
    getter: GETTER, url: str, headers: dict[str, str]
) -> dict[str, Any] | None:
    """Secondary catalogs may 404; transport / auth failures stay fatal."""
    try:
        response = getter(url, headers)
    except httpx.HTTPError as exc:
        raise SwarmApiError(f"API unreachable at {url}: {exc}") from exc
    if response.status_code == 404:
        return None
    return _json_object(response, url)


def _seats_from_blueprints(payload: dict[str, Any]) -> list[RailSeat]:
    seats: list[RailSeat] = []
    for row in payload.get("data") or []:
        if not isinstance(row, dict) or not is_rail_seat(row):
            continue
        seat_id = str(row.get("id") or "").strip()
        if not seat_id:
            continue
        name = str(row.get("name") or seat_id).strip() or seat_id
        kind = str(row.get("kind") or "blueprint").strip() or "blueprint"
        seats.append(RailSeat(id=seat_id, name=name, kind=kind, source="blueprints"))
    return seats


def _seats_from_cli_agents(payload: dict[str, Any]) -> list[RailSeat]:
    seats: list[RailSeat] = []
    for row in payload.get("rail") or []:
        if not isinstance(row, dict):
            continue
        seat_id = str(row.get("id") or "").strip()
        if not seat_id:
            continue
        name = str(row.get("name") or seat_id).strip() or seat_id
        kind = str(row.get("kind") or "cli").strip() or "cli"
        seats.append(RailSeat(id=seat_id, name=name, kind=kind, source="cli-agents"))
    return seats


def _seats_from_remotes(payload: dict[str, Any]) -> list[RailSeat]:
    seats: list[RailSeat] = []
    # SPA Settings / rail use ``configured`` (opt-in). ``data`` includes defaults.
    for row in payload.get("configured") or []:
        if not isinstance(row, dict):
            continue
        seat_id = str(row.get("id") or "").strip()
        if not seat_id:
            continue
        name = str(row.get("title") or row.get("label") or seat_id).strip() or seat_id
        seats.append(RailSeat(id=seat_id, name=name, kind="remote", source="remotes"))
    return seats


def _dedupe(seats: list[RailSeat]) -> list[RailSeat]:
    seen: set[str] = set()
    out: list[RailSeat] = []
    for seat in seats:
        if seat.id in seen:
            continue
        seen.add(seat.id)
        out.append(seat)
    return out


def list_rail_agents(
    *,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = 8.0,
    getter: GETTER | None = None,
) -> list[RailSeat]:
    """List AGENTS-rail seats from the running swarm-api.

    ``GET /v1/blueprints/`` is required. ``/v1/cli-agents/`` and
    ``/v1/remotes/`` merge when present. Teams / Herdr members are Wave 1.
    """
    base = resolve_base_url(base_url)
    auth = token if token is not None else resolve_token()
    headers = _headers(auth)

    def default_getter(url: str, hdrs: dict[str, str]) -> httpx.Response:
        with httpx.Client(timeout=timeout) as client:
            return client.get(url, headers=hdrs)

    fetch = getter or default_getter

    blueprints_url = _url(base, "/v1/blueprints/")
    payload = _json_object(_request(fetch, blueprints_url, headers), blueprints_url)
    seats = _seats_from_blueprints(payload)

    cli_payload = _optional_json(fetch, _url(base, "/v1/cli-agents/"), headers)
    if cli_payload is not None:
        seats.extend(_seats_from_cli_agents(cli_payload))

    remotes_payload = _optional_json(fetch, _url(base, "/v1/remotes/"), headers)
    if remotes_payload is not None:
        seats.extend(_seats_from_remotes(remotes_payload))

    return _dedupe(seats)
