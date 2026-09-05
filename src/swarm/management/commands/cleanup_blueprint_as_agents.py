"""Archive leftover seed/demo blueprint-as-agent rows (REQ-170).

Default is dry-run. Pass --apply to write. Never deletes user-created
agents. Idempotent: already-archived / inactive rows are skipped.

Discovery packages are not deleted — they stay on GET /v1/blueprints/ and
``?blueprint=``. The rail filter (metadata.rail) is the display SoT.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from swarm.core.rail_seats import (
    CleanupPlan,
    apply_custom_library_archive,
    apply_marketplace_archive,
    plan_blueprint_as_agent_cleanup,
)


class Command(BaseCommand):
    help = (
        "Dry-run (default) or --apply archive of leftover seed/demo "
        "blueprint-as-agent rows. Does not delete user agents or recipe packages."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write archives. Default is dry-run (no writes).",
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
        marketplace_rows = _load_marketplace()
        custom_rows, library = _load_custom_library()
        discovery = _load_discovery()
        plan = plan_blueprint_as_agent_cleanup(
            marketplace=marketplace_rows,
            custom=custom_rows,
            discovery=discovery,
        )
        if as_json:
            self.stdout.write(json.dumps(_plan_payload(plan, apply), indent=2))
        else:
            _print_plan(self, plan, apply)
        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run — no writes. Re-run with --apply to archive."))
            return
        _apply_plan(plan, marketplace_rows, custom_rows, library)
        self.stdout.write(self.style.SUCCESS("Archive applied (idempotent; no deletes)."))


def _load_marketplace() -> list[dict[str, Any]]:
    try:
        from swarm.models.core_models import Blueprint as MarketplaceBlueprint
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for obj in MarketplaceBlueprint.objects.all():
            rows.append(
                {
                    "id": obj.name,
                    "name": obj.name,
                    "title": obj.title,
                    "is_active": obj.is_active,
                    "manifest_data": dict(obj.manifest_data or {}),
                    "source": obj.source,
                }
            )
    except Exception:
        return []
    return rows


def _load_custom_library() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from swarm.views.blueprint_library_views import get_user_blueprint_library
    except Exception:
        return [], {"installed": [], "custom": []}
    try:
        library = get_user_blueprint_library()
    except Exception:
        return [], {"installed": [], "custom": []}
    custom = [item for item in library.get("custom", []) if isinstance(item, dict)]
    return custom, library


def _load_discovery() -> dict[str, Any]:
    try:
        from swarm.views.utils import _load_all_blueprint_metadata_sync
    except Exception:
        return {}
    try:
        found = _load_all_blueprint_metadata_sync()
    except Exception:
        return {}
    return found if isinstance(found, dict) else {}


def _apply_plan(
    plan: CleanupPlan,
    marketplace_rows: list[dict[str, Any]],
    custom_rows: list[dict[str, Any]],
    library: dict[str, Any],
) -> None:
    archive_market = {
        action.id.lower().replace("-", "_")
        for action in plan.actions
        if action.store == "marketplace"
    }
    if archive_market:
        try:
            from swarm.models.core_models import Blueprint as MarketplaceBlueprint

            for obj in MarketplaceBlueprint.objects.all():
                ident = str(obj.name or "").strip().lower().replace("-", "_")
                if ident not in archive_market:
                    continue
                obj.is_active = False
                manifest = dict(obj.manifest_data or {})
                manifest["archived_reason"] = "req-170-blueprint-as-agent"
                obj.manifest_data = manifest
                obj.save(update_fields=["is_active", "manifest_data", "updated_at"])
        except Exception:
            apply_marketplace_archive(marketplace_rows, plan)

    archive_custom = {
        action.id.lower().replace("-", "_")
        for action in plan.actions
        if action.store == "custom_library"
    }
    if archive_custom:
        updated = apply_custom_library_archive(custom_rows, plan)
        library["custom"] = updated
        try:
            from swarm.views.blueprint_library_views import save_user_blueprint_library

            save_user_blueprint_library(library)
        except Exception:
            pass


def _plan_payload(plan: CleanupPlan, apply: bool) -> dict[str, Any]:
    return {
        "dry_run": not apply,
        "archive": [
            {"store": a.store, "id": a.id, "action": a.action, "reason": a.reason}
            for a in plan.actions
        ],
        "kept": [
            {"store": a.store, "id": a.id, "reason": a.reason} for a in plan.kept
        ],
        "already": [
            {"store": a.store, "id": a.id, "reason": a.reason} for a in plan.already
        ],
        "catalog_only_discovery": plan.catalog_only,
        "deletes": [],
    }


def _print_plan(cmd: BaseCommand, plan: CleanupPlan, apply: bool) -> None:
    mode = "APPLY" if apply else "DRY-RUN"
    cmd.stdout.write(f"REQ-170 blueprint-as-agent cleanup ({mode})")
    if not plan.actions:
        cmd.stdout.write("Nothing to archive (idempotent).")
    for action in plan.actions:
        cmd.stdout.write(f"  archive {action.store}:{action.id} — {action.reason}")
    for action in plan.kept:
        cmd.stdout.write(f"  keep {action.store}:{action.id} — {action.reason}")
    for action in plan.already:
        cmd.stdout.write(f"  skip {action.store}:{action.id} — {action.reason}")
    if plan.catalog_only:
        cmd.stdout.write(
            f"  catalog-only discovery ids (not deleted): {len(plan.catalog_only)}"
        )
