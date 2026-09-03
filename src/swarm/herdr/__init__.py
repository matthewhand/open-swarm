"""Herdr CLI client (REQ-21).

Open Swarm drives Herdr as a **member kind=herdr** without owning the TUI.
This package wraps the official ``herdr`` CLI only — it does **not** speak the
unix-socket protocol, and it is **not** Hermes, OMB, or Rakazo.

Default target is the Herdr already on this host (no ``--remote``; local server
+ unix sockets, typically ``~/.config/herdr/``). Set ``remote`` to prefix every
call with ``herdr --remote <value>``.

Cloud CI and unit tests must mock the CLI. Do not point tests at a live TUI
(especially a WORKING grok pane). Proven on-host shape:
``herdr agent prompt w3:p1 HERDR_PING_OK`` → ``type: agent_prompted``.
"""

from swarm.herdr.client import (
    AGENT_PROMPTED,
    MEMBER_KIND,
    WAIT_UNTIL_STATES,
    HerdrBlockedError,
    HerdrCLIError,
    HerdrClient,
    HerdrError,
    extract_prompt_type,
    members_from_agent_list,
    members_from_workspace_list,
)

__all__ = [
    "AGENT_PROMPTED",
    "MEMBER_KIND",
    "WAIT_UNTIL_STATES",
    "HerdrBlockedError",
    "HerdrCLIError",
    "HerdrClient",
    "HerdrError",
    "extract_prompt_type",
    "members_from_agent_list",
    "members_from_workspace_list",
]
