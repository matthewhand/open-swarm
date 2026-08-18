"""Creator save path: user blueprints land under get_user_blueprints_dir() (XDG)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


VALID_AGENT_CODE = '''
from collections.abc import AsyncGenerator
from typing import Any
from swarm.core.blueprint_base import BlueprintBase

class MyTestAgent(BlueprintBase):
    metadata = {
        "name": "My Test Agent",
        "description": "unit test agent",
        "version": "1.0.0",
    }

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        yield {"messages": [{"role": "assistant", "content": "ok"}]}
'''


def _login_client():
    User = get_user_model()
    User.objects.create_user(username="creator_save", password="cpass")
    client = Client()
    assert client.login(username="creator_save", password="cpass")
    return client


@pytest.mark.django_db
class TestCreatorSavePath:
    def test_save_custom_agent_writes_under_user_blueprints_dir(
        self, tmp_path, monkeypatch
    ):
        """save_custom_agent must write under SWARM_USER_DATA_DIR/blueprints, not cwd."""
        data_dir = tmp_path / "swarm_data"
        monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
        monkeypatch.delenv("SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY", raising=False)

        # Isolate cwd so a relative user_blueprints/ write would be detectable
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        from swarm.core.paths import get_user_blueprints_dir

        expected_root = get_user_blueprints_dir()
        assert expected_root == data_dir / "blueprints"

        client = _login_client()
        resp = client.post(
            "/agent-creator/save/",
            data=json.dumps({
                "name": "My Test Agent",
                "code": VALID_AGENT_CODE,
                "description": "unit test",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body.get("success") is True
        assert body.get("blueprint_id") == "my_test_agent"

        saved = Path(body["path"])
        assert saved.is_absolute()
        assert saved.exists()
        assert expected_root in saved.parents or saved.parent == expected_root / "my_test_agent"
        assert str(saved).startswith(str(expected_root.resolve()))
        assert saved.name == "blueprint_my_test_agent.py"
        assert saved.read_text() == VALID_AGENT_CODE

        # Must NOT write only under cwd/user_blueprints
        cwd_only = cwd / "user_blueprints" / "my_test_agent" / "blueprint_my_test_agent.py"
        assert not cwd_only.exists()

        # Discovery-off guidance
        msg = body.get("message", "")
        assert "SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY" in msg
        assert "true" in msg.lower() or "write-only" in msg.lower()

    def test_save_custom_agent_discovery_on_message(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY", "true")
        monkeypatch.chdir(tmp_path)

        client = _login_client()
        resp = client.post(
            "/agent-creator/save/",
            data=json.dumps({
                "name": "Enabled Agent",
                "code": VALID_AGENT_CODE.replace("My Test Agent", "Enabled Agent"),
                "description": "d",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        assert "discovery is enabled" in body.get("message", "").lower()
        assert body["blueprint_id"] == "enabled_agent"
        assert Path(body["path"]).exists()

    def test_save_team_swarm_writes_under_user_blueprints_dir(
        self, tmp_path, monkeypatch
    ):
        data_dir = tmp_path / "swarm_data"
        monkeypatch.setenv("SWARM_USER_DATA_DIR", str(data_dir))
        monkeypatch.delenv("SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY", raising=False)
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        from swarm.core.paths import get_user_blueprints_dir

        expected_root = get_user_blueprints_dir()
        client = _login_client()
        payload = {
            "name": "Alpha Team",
            "description": "two-bot team for path test",
            "agents": [
                {"name": "bot_a", "system_prompt": "You are bot a."},
                {"name": "bot_b", "system_prompt": "You are bot b."},
            ],
        }
        resp = client.post(
            "/team-creator/save/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body.get("success") is True
        assert body.get("blueprint_id") == "alpha-team"

        saved = Path(body["path"])
        assert saved.is_absolute()
        assert saved.exists()
        assert str(saved).startswith(str(expected_root.resolve()))
        assert not (cwd / "user_blueprints" / "alpha-team").exists()
        assert "SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY" in body.get("message", "")

    def test_get_available_agents_scans_user_blueprints_dir(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SWARM_USER_DATA_DIR", str(tmp_path / "data"))
        from swarm.core.paths import get_user_blueprints_dir
        from swarm.views.agent_creator_views import _get_available_agents

        root = get_user_blueprints_dir()
        custom = root / "my_saved_agent"
        custom.mkdir(parents=True)
        (custom / "blueprint_my_saved_agent.py").write_text("# stub\n")

        names = {a["name"] for a in _get_available_agents()}
        assert "my_saved_agent" in names
        assert "codey" in names  # builtin still present
