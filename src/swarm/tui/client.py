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


# Wave 1b: the rail groups seats under the four user-facing kind sections
# (README "Kinds lock" / ADR-006). Teams are a Blueprint subtype and Herdr is
# a Remote implementation (README "Team = Blueprint subtype"; ADR-011), so
# their seats classify into Blueprint / Remote rather than extra headings.
RAIL_KIND_SECTIONS: tuple[str, ...] = ("CLI", "API", "Blueprint", "Remote")

_RAIL_SECTION_BY_KIND = {
    "cli": "CLI",
    "api": "API",
    "blueprint": "Blueprint",
    "team": "Blueprint",
    "remote": "Remote",
    "herdr": "Remote",
}


def rail_section(kind: str) -> str:
    """Map a seat ``kind`` to its rail kind-section heading (Wave 1b)."""
    return _RAIL_SECTION_BY_KIND.get((kind or "").strip().lower(), "Blueprint")


def sectioned_seats(
    seats: list[RailSeat],
) -> list[tuple[str, list[RailSeat]]]:
    """Group seats into the four kind sections; empty sections are omitted."""
    buckets: dict[str, list[RailSeat]] = {}
    for seat in seats:
        buckets.setdefault(rail_section(seat.kind), []).append(seat)
    return [
        (label, buckets[label])
        for label in RAIL_KIND_SECTIONS
        if label in buckets
    ]


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _transport_error_message(url: str, exc: httpx.HTTPError) -> str:
    """Wave 1c: name the failure and how to point the TUI elsewhere."""
    return (
        f"API unreachable at {url}: {exc}. "
        "Is the swarm-api running there? If not, set SWARM_API_BASE "
        f"(default {DEFAULT_BASE_URL})."
    )


def _request(getter: GETTER, url: str, headers: dict[str, str]) -> httpx.Response:
    try:
        return getter(url, headers)
    except httpx.HTTPError as exc:
        raise SwarmApiError(_transport_error_message(url, exc)) from exc


def _auth_failure_message(status: int, auth_sent: bool) -> str:
    """Wave 1c: 401/403 named, and the cause told apart — no token vs rejected.

    Env-var **names** only; a raw token is never echoed back to the terminal.
    """
    if auth_sent:
        return (
            f"API auth failed ({status}) \u2014 the Bearer token sent is not "
            "accepted by the swarm-api. Set API_AUTH_TOKEN or SWARM_API_KEY to "
            "a token the API accepts (env-var names only)."
        )
    return (
        f"API auth required ({status}) \u2014 the swarm-api has auth enabled but this "
        "shell sets no API_AUTH_TOKEN / SWARM_API_KEY (env-var names only)."
    )


def _json_object(
    response: httpx.Response, url: str, *, auth_sent: bool
) -> dict[str, Any]:
    if response.status_code in {401, 403}:
        raise SwarmApiError(
            f"{_auth_failure_message(response.status_code, auth_sent)} at {url}"
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
    getter: GETTER,
    url: str,
    headers: dict[str, str],
    *,
    auth_sent: bool,
) -> dict[str, Any] | None:
    """Secondary catalogs may 404; transport / auth failures stay fatal."""
    try:
        response = getter(url, headers)
    except httpx.HTTPError as exc:
        raise SwarmApiError(_transport_error_message(url, exc)) from exc
    if response.status_code == 404:
        return None
    return _json_object(response, url, auth_sent=auth_sent)


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


def _seats_from_team_rosters(payload: dict[str, Any]) -> list[RailSeat]:
    """Each saved roster is one team seat, namespaced ``team:<id>`` (SPA rail id).

    Nested teams (a roster listed as a ``kind=team`` member of another roster)
    are surfaced through their parent, exactly like the SPA rail's root teams.
    """
    rosters = [r for r in payload.get("data") or [] if isinstance(r, dict)]
    child_ids = {
        str(member.get("team_id") or member.get("id") or "").strip()
        for roster in rosters
        for member in roster.get("members") or []
        if isinstance(member, dict) and str(member.get("kind") or "").strip() == "team"
    }
    seats: list[RailSeat] = []
    for roster in rosters:
        roster_id = str(roster.get("id") or "").strip()
        if not roster_id or roster_id in child_ids:
            continue
        name = str(roster.get("name") or roster_id).strip() or roster_id
        seats.append(
            RailSeat(
                id=f"team:{roster_id}",
                name=name,
                kind="team",
                source="team-rosters",
            )
        )
    return seats


def _seats_from_herdr_agents(payload: dict[str, Any]) -> list[RailSeat]:
    """Persisted Herdr members become rail seats ``herdr:<name>`` (SPA id)."""
    seats: list[RailSeat] = []
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        seats.append(
            RailSeat(id=f"herdr:{name}", name=name, kind="herdr", source="herdr-agents")
        )
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

    ``GET /v1/blueprints/`` (rail filter) is required. ``/v1/cli-agents/``
    ``.rail``, ``/v1/remotes/`` ``.configured``, ``/v1/team-rosters/`` and
    ``/v1/herdr-agents/`` merge when present (Wave 1b parity with the SPA
    AgentSidebar). Seats dedupe by id; teams keep their ``team:`` / ``herdr:``
    rail ids so a roster never collides with a catalog seat of the same name.

    Auth matches the WebUI REST contract (Wave 1c): ``API_AUTH_TOKEN`` or
    ``SWARM_API_KEY`` from the shell becomes ``Authorization: Bearer``. A
    401/403 names the cause (no token set vs token rejected) and never echoes
    the value; a connection failure names the origin and ``SWARM_API_BASE``.
    Empty catalogs stay empty — no agents are ever invented.
    """
    base = resolve_base_url(base_url)
    auth = token if token is not None else resolve_token()
    auth_sent = auth is not None
    headers = _headers(auth)

    def default_getter(url: str, hdrs: dict[str, str]) -> httpx.Response:
        with httpx.Client(timeout=timeout) as client:
            return client.get(url, headers=hdrs)

    fetch = getter or default_getter

    blueprints_url = _url(base, "/v1/blueprints/")
    payload = _json_object(
        _request(fetch, blueprints_url, headers), blueprints_url, auth_sent=auth_sent
    )
    seats = _seats_from_blueprints(payload)

    cli_payload = _optional_json(
        fetch, _url(base, "/v1/cli-agents/"), headers, auth_sent=auth_sent
    )
    if cli_payload is not None:
        seats.extend(_seats_from_cli_agents(cli_payload))

    remotes_payload = _optional_json(
        fetch, _url(base, "/v1/remotes/"), headers, auth_sent=auth_sent
    )
    if remotes_payload is not None:
        seats.extend(_seats_from_remotes(remotes_payload))

    teams_payload = _optional_json(
        fetch, _url(base, "/v1/team-rosters/"), headers, auth_sent=auth_sent
    )
    if teams_payload is not None:
        seats.extend(_seats_from_team_rosters(teams_payload))

    herdr_payload = _optional_json(
        fetch, _url(base, "/v1/herdr-agents/"), headers, auth_sent=auth_sent
    )
    if herdr_payload is not None:
        seats.extend(_seats_from_herdr_agents(herdr_payload))

    return _dedupe(seats)
