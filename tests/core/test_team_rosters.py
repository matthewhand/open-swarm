"""REQ-28 roster persist: kind team|herdr and chief_of_staff role."""

import pytest

from swarm.core.team_rosters import (
    MEMBER_KINDS,
    normalize_member,
    normalize_roster,
    reset_team_rosters,
    upsert_roster,
)


@pytest.fixture(autouse=True)
def _clean_rosters(tmp_path, monkeypatch):
    from swarm.core import team_rosters as store

    cfg = tmp_path / "cfg"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "get_user_config_dir_for_swarm", lambda: cfg)
    monkeypatch.setattr(store, "ensure_swarm_directories_exist", lambda: None)
    reset_team_rosters()
    yield
    reset_team_rosters()


def test_member_kinds_include_team_and_herdr():
    assert MEMBER_KINDS == ("api", "cli", "remote", "team", "herdr")


def test_normalize_kind_team_requires_team_id():
    member = normalize_member(
        {"id": "research", "kind": "team", "role": "default", "source": "team:research"}
    )
    assert member["kind"] == "team"
    assert member["team_id"] == "research"
    assert member["source"] == "team:research"


def test_role_cos_persists_on_member():
    member = normalize_member({"id": "pat", "kind": "api", "role": "cos"})
    assert member["role"] == "chief_of_staff"
    assert member["kind"] == "api"
    assert set(member) >= {"id", "kind", "role", "source"}


def test_persist_nested_and_herdr_members(tmp_path, monkeypatch):
    stored = upsert_roster(
        {
            "id": "office",
            "name": "Office",
            "members": [
                {"id": "cos", "kind": "api", "role": "chief", "source": "blueprint:cos"},
                {"id": "research", "kind": "team", "team_id": "research", "role": "default"},
                {"id": "w3p1", "kind": "herdr", "role": "default", "source": "herdr:w3:p1"},
            ],
        }
    )
    kinds = {m["id"]: m for m in stored["members"]}
    assert kinds["research"]["kind"] == "team"
    assert kinds["research"]["team_id"] == "research"
    assert kinds["w3p1"]["kind"] == "herdr"
    assert kinds["cos"]["role"] == "chief_of_staff"
    for member in stored["members"]:
        assert set(member) >= {"id", "kind", "role", "source"}


def test_agent_team_alias_accepted():
    roster = normalize_roster(
        {
            "id": "alpha",
            "agent_team": [{"id": "a", "kind": "cli", "role": "skeptic"}],
        }
    )
    assert roster["members"][0]["kind"] == "cli"
    assert roster["members"][0]["role"] == "skeptic"


def test_self_nest_rejected():
    with pytest.raises(ValueError, match="cannot nest itself"):
        normalize_roster(
            {
                "id": "loop",
                "members": [{"id": "loop", "kind": "team", "team_id": "loop"}],
            }
        )
