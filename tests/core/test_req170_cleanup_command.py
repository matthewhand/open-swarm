"""REQ-170: management command dry-run (no writes, no deletes)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from swarm.core.rail_seats import CleanupAction, CleanupPlan


def test_cleanup_command_dry_run_default_writes_nothing():
    plan = CleanupPlan(
        actions=[
            CleanupAction("marketplace", "codey", "archive", "seed leftover"),
        ],
        kept=[
            CleanupAction("custom_library", "my_helper", "keep", "user-created"),
        ],
        catalog_only=["poets", "cli_fusion"],
    )
    apply = []

    def _capture(*args, **kwargs):
        apply.append((args, kwargs))

    with (
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_marketplace",
            return_value=[{"id": "codey", "is_active": True}],
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_custom_library",
            return_value=([{"id": "my_helper"}], {"custom": [{"id": "my_helper"}]}),
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_discovery",
            return_value={"poets": {"metadata": {}}},
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents.plan_blueprint_as_agent_cleanup",
            return_value=plan,
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._apply_plan",
            side_effect=_capture,
        ),
    ):
        out = StringIO()
        call_command("cleanup_blueprint_as_agents", stdout=out)

    text = out.getvalue()
    assert "DRY-RUN" in text
    assert "codey" in text
    assert "my_helper" in text
    assert apply == []


def test_cleanup_command_json_dry_run_has_no_deletes():
    plan = CleanupPlan(
        actions=[CleanupAction("marketplace", "poets", "archive", "demo")],
        catalog_only=["poets"],
    )
    with (
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_marketplace",
            return_value=[],
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_custom_library",
            return_value=([], {"custom": []}),
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents._load_discovery",
            return_value={},
        ),
        patch(
            "swarm.management.commands.cleanup_blueprint_as_agents.plan_blueprint_as_agent_cleanup",
            return_value=plan,
        ),
    ):
        out = StringIO()
        call_command("cleanup_blueprint_as_agents", "--json", stdout=out)

    payload = out.getvalue()
    assert '"dry_run": true' in payload
    assert '"deletes": []' in payload
    assert "poets" in payload
