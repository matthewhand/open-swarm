"""Hard-delete Support/CoS archived seats older than ~30 days (REQ-154).

Default is dry-run. Pass ``--apply`` to write.

Chats are **not** hard-deleted here — they follow ``SWARM_CHAT_MAX_AGE_DAYS``
(Settings trash). Prefs (Hidden Bots / favourites) drop purged ids. Team
roster members with those ids are stripped.

See ``docs/AGENT_LIFECYCLE.md``.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from swarm.core.agent_lifecycle import (
    apply_purge,
    default_stores,
    purge_due_rows,
    retention_days,
)


class Command(BaseCommand):
    help = (
        "purge_archived_agents: dry-run (default) or --apply purge of archived "
        "agents older than SWARM_ARCHIVED_AGENT_RETENTION_DAYS (default 30). "
        "Does not hard-delete chats."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Hard-delete due rows. Default is dry-run (no writes).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override retention days (default: env or 30).",
        )
        parser.add_argument(
            "--include-unstamped",
            action="store_true",
            help="Also purge archived rows that have no archived_at stamp.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Print the plan as JSON (ids/reasons only; no secrets).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply = bool(options.get("apply"))
        as_json = bool(options.get("as_json"))
        days = options.get("days")
        stores = default_stores()
        plan = purge_due_rows(
            library=stores.library,
            remotes=stores.remotes,
            days=days,
            include_unstamped=bool(options.get("include_unstamped")),
        )
        payload = {
            "apply": apply,
            "retention_days": plan.get("retention_days", retention_days()),
            "cutoff": plan.get("cutoff"),
            "due": plan.get("due") or [],
            "kept": plan.get("kept") or [],
            "chats_policy": "retained_until_SWARM_CHAT_MAX_AGE_DAYS",
            "prefs_policy": "strip_hidden_and_favourites_on_apply",
        }
        if apply:
            result = apply_purge(
                plan,
                library=stores.library,
                remotes=stores.remotes,
                remotes_cfg=stores.remotes_cfg,
                remotes_path=stores.remotes_path,
                persist=True,
                strip_rosters=True,
                strip_prefs=True,
            )
            payload["removed"] = result.get("removed") or []
        if as_json:
            self.stdout.write(json.dumps(payload, indent=2))
        else:
            _print_plan(self, payload, apply)
        if not apply:
            self.stdout.write(
                self.style.WARNING("Dry-run — no writes. Re-run with --apply to purge.")
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                "Purge applied. Chats left on SWARM_CHAT_MAX_AGE_DAYS; prefs/rosters stripped."
            )
        )


def _print_plan(cmd: BaseCommand, payload: dict[str, Any], apply: bool) -> None:
    days = payload.get("retention_days")
    cmd.stdout.write(f"Retention: {days} day(s). Cutoff: {payload.get('cutoff')}")
    due = payload.get("due") or []
    kept = payload.get("kept") or []
    if due:
        cmd.stdout.write(cmd.style.NOTICE(f"Due ({len(due)}):"))
        for row in due:
            cmd.stdout.write(f"  - {row.get('store')}:{row.get('id')} ({row.get('reason')})")
    else:
        cmd.stdout.write("Due: none")
    if kept:
        cmd.stdout.write(f"Kept inside window or protected: {len(kept)}")
    if apply:
        removed = payload.get("removed") or []
        cmd.stdout.write(f"Removed: {len(removed)}")
