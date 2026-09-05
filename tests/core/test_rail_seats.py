"""REQ-170: rail flag default-deny + cleanup dry-run (no deletes)."""

from __future__ import annotations

from swarm.core.rail_seats import (
    DEMO_CATALOG_IDS,
    apply_custom_library_archive,
    apply_marketplace_archive,
    is_protected_user_agent,
    is_seed_demo_row,
    metadata_rail,
    plan_blueprint_as_agent_cleanup,
)


def test_metadata_rail_default_denies_missing_and_false():
    assert metadata_rail(None) is False
    assert metadata_rail({}) is False
    assert metadata_rail({"rail": False}) is False
    assert metadata_rail({"rail": "true"}) is False
    assert metadata_rail({"rail": True}) is True


def test_demo_catalog_ids_cover_audit_fixtures():
    for ident in (
        "poets",
        "chucks_angels",
        "django_chat",
        "moa",
        "mixture_of_agents",
        "cli_fusion",
        "swarm_ensemble",
        "software_dev",
        "codey",
    ):
        assert ident in DEMO_CATALOG_IDS


def test_cleanup_dry_run_archives_demo_leftovers_keeps_user_agents():
    marketplace = [
        {"id": "codey", "name": "codey", "is_active": True},
        {"id": "poets", "name": "poets", "is_active": True},
        {"id": "chucks_angels", "name": "chucks_angels", "is_active": False},
    ]
    custom = [
        {"id": "cli_fusion", "name": "cli_fusion", "code": ""},
        {"id": "my_helper", "name": "My Helper", "code": "print('hi')"},
        {"id": "desk_bot", "name": "Desk", "source": "wizard"},
        {"id": "opt_in", "name": "poets", "rail": True},
    ]
    discovery = {
        "poets": {"metadata": {"name": "poets"}},
        "support": {"metadata": {"name": "support", "rail": True}},
        "codey": {"metadata": {"name": "codey"}},
    }

    plan = plan_blueprint_as_agent_cleanup(
        marketplace=marketplace,
        custom=custom,
        discovery=discovery,
    )
    archive_ids = {action.id for action in plan.actions}
    assert "codey" in archive_ids
    assert "poets" in archive_ids
    assert "cli_fusion" in archive_ids
    kept_ids = {action.id for action in plan.kept}
    assert "my_helper" in kept_ids
    assert "desk_bot" in kept_ids
    assert "opt_in" in kept_ids
    already_ids = {action.id for action in plan.already}
    assert "chucks_angels" in already_ids
    assert "poets" in plan.catalog_only
    assert "codey" in plan.catalog_only
    assert "support" not in plan.catalog_only

    # Dry-run: planners do not mutate inputs.
    assert marketplace[0]["is_active"] is True
    assert "archived" not in custom[0]


def test_cleanup_apply_is_idempotent_and_never_deletes():
    marketplace = [
        {"id": "codey", "name": "codey", "is_active": True, "manifest_data": {}},
        {"id": "my_blueprint", "name": "my_blueprint", "is_active": True},
    ]
    custom = [
        {"id": "poets", "name": "poets"},
        {"id": "office_bot", "name": "Office Bot", "code": "class X: ..."},
    ]
    plan = plan_blueprint_as_agent_cleanup(marketplace=marketplace, custom=custom)
    once = apply_marketplace_archive(marketplace, plan)
    twice = apply_marketplace_archive(once, plan)
    custom_once = apply_custom_library_archive(custom, plan)
    custom_twice = apply_custom_library_archive(custom_once, plan)

    by_id = {row["id"]: row for row in twice}
    assert by_id["codey"]["is_active"] is False
    assert by_id["my_blueprint"]["is_active"] is True
    assert len(twice) == 2
    custom_by_id = {row["id"]: row for row in custom_twice}
    assert custom_by_id["poets"]["archived"] is True
    assert "archived" not in custom_by_id["office_bot"]
    assert len(custom_twice) == 2

    again = plan_blueprint_as_agent_cleanup(marketplace=twice, custom=custom_twice)
    assert again.actions == []
    assert any(row.id == "codey" for row in again.already)
    assert any(row.id == "poets" for row in again.already)


def test_protected_user_agents_are_not_seed_demo_rows():
    assert is_protected_user_agent({"id": "support"}) is True
    assert is_protected_user_agent({"id": "my_helper"}) is True
    assert is_protected_user_agent({"id": "poets", "rail": True}) is True
    assert is_seed_demo_row({"id": "poets"}) is True
    assert is_seed_demo_row({"id": "my_helper"}) is False
