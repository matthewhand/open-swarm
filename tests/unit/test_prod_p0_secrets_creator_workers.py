"""Production P0: settings redaction, creator write auth, workers=1 helper."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse


@pytest.mark.django_db
class TestSettingsRedaction:
    def _leaky_config(self):
        return {
            "llm": {
                "openai": {"api_key": "sk-super-secret-key-should-not-leak", "model": "gpt-4"},
            },
            "profiles": {
                "prod": {"api_key": "sk-profile-secret", "base_url": "https://api.openai.com/v1"},
            },
        }

    def _client_with_leaky_settings(self):
        User = get_user_model()
        User.objects.create_user(username="setuser", password="setpass")
        client = Client()
        assert client.login(username="setuser", password="setpass")
        from swarm.views import settings_manager as sm_mod

        mgr = sm_mod.SettingsManager()
        return client, sm_mod, mgr

    def test_settings_api_hides_profile_secrets(self, monkeypatch):
        client, sm_mod, mgr = self._client_with_leaky_settings()
        with patch("swarm.views.settings_manager.load_config", return_value=self._leaky_config()):
            with patch.object(sm_mod, "settings_manager", mgr):
                resp = client.get("/settings/api/")
        assert resp.status_code == 200
        body = resp.content.decode()
        assert "sk-super-secret-key-should-not-leak" not in body
        assert "sk-profile-secret" not in body
        assert "***HIDDEN***" in body or "REDACTED" in body or "***SET***" in body

    def test_settings_dashboard_json_script_hides_secrets(self):
        """Dashboard embeds settings_groups via json_script for viewObject — must redact."""
        client, sm_mod, mgr = self._client_with_leaky_settings()
        with patch("swarm.views.settings_manager.load_config", return_value=self._leaky_config()):
            with patch.object(sm_mod, "settings_manager", mgr):
                resp = client.get("/settings/")
        assert resp.status_code == 200
        body = resp.content.decode()
        assert "sk-super-secret-key-should-not-leak" not in body
        assert "sk-profile-secret" not in body
        assert "swarm-settings-data" in body


@pytest.mark.django_db
class TestCreatorWriteAuth:
    def test_save_custom_agent_requires_login(self):
        client = Client()
        resp = client.post(
            "/agent-creator/save/",
            data='{"name":"x","code":"class A(BlueprintBase):\\n  pass\\n"}',
            content_type="application/json",
        )
        # login_required → redirect to login or 403
        assert resp.status_code in (302, 401, 403)

    def test_save_team_swarm_requires_login(self):
        client = Client()
        payload = {
            "name": "Evil Team",
            "description": "team",
            "agents": [
                {"name": "a", "system_prompt": "You are a"},
                {"name": "b", "system_prompt": "You are b"},
            ],
        }
        resp = client.post(
            "/team-creator/save/",
            data=json_dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code in (302, 401, 403)

    def test_save_custom_agent_blocks_exec_in_source(self, tmp_path, monkeypatch):
        User = get_user_model()
        User.objects.create_user(username="creator", password="cpass")
        client = Client()
        assert client.login(username="creator", password="cpass")
        monkeypatch.chdir(tmp_path)
        code = '''
from swarm.core.blueprint_base import BlueprintBase
from typing import Any, AsyncGenerator
class Evil(BlueprintBase):
    metadata = {"name": "evil"}
    async def run(self, messages, stream=False) -> AsyncGenerator:
        exec("print(1)")
        if False:
            yield {}
'''
        resp = client.post(
            "/agent-creator/save/",
            data=json_dumps({"name": "EvilAgent", "code": code, "description": "x"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data.get("success") is False
        assert "exec" in data.get("error", "").lower() or "unsandboxed" in data.get("error", "").lower()

    def test_validate_blueprint_code_does_not_exec(self):
        """Structural: validator uses AST only — no exec() in module path for validation."""
        from swarm.views.agent_creator_views import BlueprintCodeValidator
        import inspect

        src = inspect.getsource(BlueprintCodeValidator.validate_blueprint_code)
        assert "exec(" not in src
        assert "exec_module" not in src
        v = BlueprintCodeValidator()
        # Valid-ish minimal code
        result = v.validate_blueprint_code("class Foo:\n    pass\n")
        assert "syntax_valid" in result


def json_dumps(obj):
    import json
    return json.dumps(obj)


class TestWorkersSingleContract:
    def test_resolved_uvicorn_workers_default_one(self, monkeypatch):
        monkeypatch.delenv("SWARM_UVICORN_WORKERS", raising=False)
        monkeypatch.delenv("SWARM_ENFORCE_SINGLE_WORKER", raising=False)
        from swarm.core.concurrency import resolved_uvicorn_workers

        assert resolved_uvicorn_workers() == 1

    def test_resolved_uvicorn_workers_refuses_multi(self, monkeypatch):
        monkeypatch.setenv("SWARM_UVICORN_WORKERS", "4")
        monkeypatch.setenv("SWARM_ENFORCE_SINGLE_WORKER", "true")
        from swarm.core.concurrency import resolved_uvicorn_workers

        with pytest.raises(ValueError, match="process-local"):
            resolved_uvicorn_workers()

    def test_resolved_uvicorn_workers_override_warns(self, monkeypatch):
        monkeypatch.setenv("SWARM_UVICORN_WORKERS", "2")
        monkeypatch.setenv("SWARM_ENFORCE_SINGLE_WORKER", "false")
        from swarm.core.concurrency import resolved_uvicorn_workers

        assert resolved_uvicorn_workers() == 2

    def test_user_blueprint_discovery_off_by_default(self, monkeypatch):
        monkeypatch.delenv("SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY", raising=False)
        monkeypatch.delenv("SWARM_BLUEPRINT_PATHS", raising=False)
        # Re-import helper
        from swarm import settings as s

        dirs = s._blueprint_extra_dirs()
        # Without allow flag, user dir should not appear (paths may still include SWARM_BLUEPRINT_PATHS only)
        from swarm.core.paths import get_user_blueprints_dir

        user = str(get_user_blueprints_dir())
        assert user not in dirs
