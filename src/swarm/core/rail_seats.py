"""REQ-170: rail seats vs blueprint catalog.

Discovery lists every ``blueprint_*.py`` as ``object=blueprint``. The AGENTS
rail is an allowlist: ``metadata.rail is True``. Missing or false means
catalog-only (Settings / Add-agent / ``?blueprint=`` / ``/v1/models``).

This is not a Django Agent archive. Live ``:8001`` had
``marketplace_blueprint`` count 0 — discovery *is* the seed. The cleanup
helpers still archive leftover marketplace / custom-library clones of the
demo recipe pack when those stores are non-empty, without deleting
user-created seats. ``django_chat`` is already retired (#419 / #828); leftover
ids stay in the denylist so a stale row cannot reappear as a rail agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

# Role seats that belong on the Grok AGENTS rail (gate/skeptic stay hide-seeded).
RAIL_ROLE_IDS = frozenset({"support", "gate", "tool_gate", "skeptic"})

# Catalog recipes that must not be peer Agent rows (audit #595 / #599).
# Includes retired django_chat leftover ids (#419 / #828).
DEMO_CATALOG_IDS = frozenset(
    {
        "poets",
        "chucks_angels",
        "django_chat",
        "django-chat",
        "moa",
        "mixture_of_agents",
        "moa_orchestrator",
        "moa-orch",
        "hybrid_moa",
        "moa_hybrid",
        "hybrid-consensus",
        "hybrid_team",
        "hybrid_swarm",
        "cli_fusion",
        "cli_ensemble",
        "cli_map",
        "cli_recurse",
        "cli_pipeline",
        "cli_roundtable",
        "cli_planner",
        "cli_orchestrator",
        "swarm_ensemble",
        "swarm_map",
        "swarm_recurse",
        "swarm_pipeline",
        "swarm_roundtable",
        "swarm_planner",
        "swarm_orchestrator",
        "software_dev",
        "software-dev",
        "codey",
        "stewie",
        "geese",
        "zeus",
        "gawd",
        "suggestion",
        "fs_introspect",
        "remote_harness",
        "harness_fleet",
        "persona_council",
        "dynamic_team",
        "agent_router",
        "jeeves",
        "rue_code",
        "whiskeytango_foxtrot",
        "cli_agent",
        "chatbot",
        "sdlc_handoff",
    }
)

USER_SOURCE_MARKERS = frozenset({"user", "wizard", "custom", "add-agent"})


def metadata_rail(meta: Mapping[str, Any] | None) -> bool:
    """True only when discovery metadata explicitly opts the recipe onto the rail."""
    if not meta:
        return False
    return meta.get("rail") is True


def row_id(row: Mapping[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("id") or row.get("name") or "").strip()


def is_protected_user_agent(item: Mapping[str, Any] | None) -> bool:
    """User-created seats must never be archived or deleted."""
    if not item:
        return False
    ident = row_id(item).lower().replace("-", "_")
    if ident in RAIL_ROLE_IDS:
        return True
    if item.get("rail") is True:
        return True
    if item.get("user_created") is True:
        return True
    source = str(item.get("source") or "").strip().lower()
    if source in USER_SOURCE_MARKERS:
        return True
    if ident and ident not in DEMO_CATALOG_IDS:
        return True
    return False


def is_seed_demo_row(item: Mapping[str, Any] | None) -> bool:
    """True for leftover seed/demo catalog clones — not real user agents."""
    if not item:
        return False
    if is_protected_user_agent(item):
        return False
    ident = row_id(item).lower().replace("-", "_")
    return ident in DEMO_CATALOG_IDS


def already_hidden(item: Mapping[str, Any] | None) -> bool:
    if not item:
        return True
    if item.get("archived") is True:
        return True
    if item.get("is_active") is False:
        return True
    return False


@dataclass(frozen=True)
class CleanupAction:
    store: str
    id: str
    action: str
    reason: str


@dataclass
class CleanupPlan:
    """Idempotent plan. Apply archives; never deletes."""

    actions: list[CleanupAction] = field(default_factory=list)
    kept: list[CleanupAction] = field(default_factory=list)
    already: list[CleanupAction] = field(default_factory=list)
    catalog_only: list[str] = field(default_factory=list)

    @property
    def archive_ids(self) -> list[str]:
        return [row.id for row in self.actions if row.action == "archive"]


def plan_blueprint_as_agent_cleanup(
    *,
    marketplace: Iterable[Mapping[str, Any]] | None = None,
    custom: Iterable[Mapping[str, Any]] | None = None,
    discovery: Mapping[str, Mapping[str, Any]] | None = None,
) -> CleanupPlan:
    """Plan archive/hide of seed/demo blueprint-as-agent leftovers.

    Dry-run safe: this function never writes. User-created rows are kept.
    Already-archived rows are skipped (idempotent).
    """
    plan = CleanupPlan()
    _collect_store(plan, "marketplace", marketplace)
    _collect_store(plan, "custom_library", custom)
    if discovery:
        for blueprint_id, info in discovery.items():
            meta = info.get("metadata") if isinstance(info, Mapping) else {}
            if not isinstance(meta, Mapping):
                meta = {}
            if metadata_rail(meta) or str(blueprint_id).lower() in RAIL_ROLE_IDS:
                continue
            plan.catalog_only.append(str(blueprint_id))
        plan.catalog_only.sort()
    return plan


def _collect_store(
    plan: CleanupPlan,
    store: str,
    rows: Iterable[Mapping[str, Any]] | None,
) -> None:
    for raw in rows or []:
        if not isinstance(raw, Mapping):
            continue
        ident = row_id(raw) or "?"
        if is_protected_user_agent(raw):
            plan.kept.append(
                CleanupAction(store, ident, "keep", "user-created or rail seat")
            )
            continue
        if not is_seed_demo_row(raw):
            plan.kept.append(
                CleanupAction(store, ident, "keep", "not a demo catalog leftover")
            )
            continue
        if already_hidden(raw):
            plan.already.append(
                CleanupAction(store, ident, "skip", "already archived or inactive")
            )
            continue
        plan.actions.append(
            CleanupAction(
                store,
                ident,
                "archive",
                "seed/demo blueprint-as-agent leftover",
            )
        )


def apply_marketplace_archive(
    rows: Iterable[Mapping[str, Any]],
    plan: CleanupPlan,
) -> list[dict[str, Any]]:
    """Return updated marketplace dicts (is_active=False). Does not delete."""
    archive = {
        action.id.lower().replace("-", "_")
        for action in plan.actions
        if action.store == "marketplace"
    }
    updated: list[dict[str, Any]] = []
    for raw in rows:
        item = dict(raw)
        ident = row_id(item).lower().replace("-", "_")
        if ident in archive:
            item["is_active"] = False
            manifest = dict(item.get("manifest_data") or {})
            manifest["archived_reason"] = "req-170-blueprint-as-agent"
            item["manifest_data"] = manifest
        updated.append(item)
    return updated


def apply_custom_library_archive(
    items: Iterable[Mapping[str, Any]],
    plan: CleanupPlan,
) -> list[dict[str, Any]]:
    """Return updated custom-library items (archived=True). Does not delete."""
    archive = {
        action.id.lower().replace("-", "_")
        for action in plan.actions
        if action.store == "custom_library"
    }
    updated: list[dict[str, Any]] = []
    for raw in items:
        item = dict(raw)
        ident = row_id(item).lower().replace("-", "_")
        if ident in archive:
            item["archived"] = True
            item["archived_reason"] = "req-170-blueprint-as-agent"
        updated.append(item)
    return updated
