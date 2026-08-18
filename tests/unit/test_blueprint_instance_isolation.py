"""Ensure get_blueprint_instance never shares mutable instances across calls."""

from __future__ import annotations

import asyncio

import pytest

from swarm.views import utils as view_utils


class _MutableBlueprint:
    def __init__(self, blueprint_id, config=None):
        self.blueprint_id = blueprint_id
        self.mutable_state = {"hits": 0}

    def set_params(self, params):
        self.params = params


@pytest.mark.asyncio
async def test_repeated_gets_return_distinct_instances(monkeypatch):
    async def _available():
        return {
            "demo": {"class_type": _MutableBlueprint, "metadata": {"name": "demo"}},
        }

    monkeypatch.setattr(view_utils, "get_available_blueprints", _available)
    monkeypatch.setattr(view_utils, "load_dynamic_registry", lambda: {})

    first = await view_utils.get_blueprint_instance("demo")
    second = await view_utils.get_blueprint_instance("demo")

    assert first is not None and second is not None
    assert first is not second
    first.mutable_state["hits"] = 1
    assert second.mutable_state["hits"] == 0


@pytest.mark.asyncio
async def test_concurrent_gets_return_distinct_instances(monkeypatch):
    async def _available():
        return {
            "demo": {"class_type": _MutableBlueprint, "metadata": {"name": "demo"}},
        }

    monkeypatch.setattr(view_utils, "get_available_blueprints", _available)
    monkeypatch.setattr(view_utils, "load_dynamic_registry", lambda: {})

    instances = await asyncio.gather(
        *(view_utils.get_blueprint_instance("demo") for _ in range(8))
    )

    assert all(inst is not None for inst in instances)
    assert len({id(inst) for inst in instances}) == len(instances)
    for i, inst in enumerate(instances):
        inst.mutable_state["hits"] = i
    assert [inst.mutable_state["hits"] for inst in instances] == list(range(8))


@pytest.mark.asyncio
async def test_no_process_global_instance_cache_attribute():
    assert not hasattr(view_utils, "_blueprint_instance_cache")
