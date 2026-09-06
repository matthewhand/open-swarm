"""``swarm-cli tui`` — Wave 0 stub. Textual interactivity is Wave 1."""

from __future__ import annotations

import json

import typer

from swarm.tui.client import (
    DEFAULT_BASE_URL,
    SwarmApiError,
    list_rail_agents,
    resolve_base_url,
)
from swarm.tui.layout import render_scaffold


def tui_cmd(
    once: bool = typer.Option(
        True,
        "--once/--interactive",
        help="Dump rail + placeholder pane and exit (Wave 0 default).",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="swarm-api origin. Default: SWARM_API_BASE or http://127.0.0.1:8000.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Rail seat id to mark selected (must exist in the API list).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print the rail list as JSON instead of the ASCII chrome.",
    ),
) -> None:
    """Herdr-like TUI client of the same HTTP API the WebUI uses (REQ-111)."""
    if not once:
        typer.echo(
            "Interactive Textual chrome is Wave 1. Use --once (default) for the "
            "Wave 0 scaffold.",
            err=True,
        )
        raise typer.Exit(code=2)

    resolved = resolve_base_url(base_url)
    try:
        seats = list_rail_agents(base_url=resolved)
    except SwarmApiError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        payload = {
            "object": "tui.rail",
            "base_url": resolved,
            "selected": agent or (seats[0].id if seats else None),
            "data": [
                {
                    "id": seat.id,
                    "name": seat.name,
                    "kind": seat.kind,
                    "source": seat.source,
                }
                for seat in seats
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(render_scaffold(seats, selected_id=agent, base_url=resolved), nl=False)


def register_tui(app: typer.Typer) -> None:
    app.command(name="tui")(tui_cmd)


# Re-export default for tests that assert we never bake :8001.
__all__ = ["DEFAULT_BASE_URL", "register_tui", "tui_cmd"]
