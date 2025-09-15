import json

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_blueprint_requirements_status_endpoint(monkeypatch, client):
    # Fake discovery with required MCP servers and env vars
    fake_discovered = {
        "demo_bp": {
            "class_type": object,  # not used by the view
            "metadata": {
                "name": "DemoBP",
                "required_mcp_servers": ["filesystem", "mcp-shell"],
                "env_vars": ["ALLOWED_PATH"],
            },
        }
    }

    def fake_discover(_dir):
        return fake_discovered

    # Fake active config: filesystem present with unresolved env; mcp-shell missing
    def fake_load_config():
        return {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "${ALLOWED_PATH}"],
                    "env": {"ALLOWED_PATH": "${ALLOWED_PATH}"},
                }
            }
        }

    from swarm.core import requirements as req
    from swarm.views import blueprint_library_views as blv

    monkeypatch.setattr(blv, "discover_blueprints", fake_discover)
    # Patch both the module reference used by the view and the requirements module
    monkeypatch.setattr(blv, "load_active_config", fake_load_config)
    monkeypatch.setattr(req, "load_active_config", fake_load_config)

    url = reverse("blueprint_requirements_status")
    resp = client.get(url)
    assert resp.status_code == 200
    payload = json.loads(resp.content)

    assert "blueprints" in payload and len(payload["blueprints"]) == 1
    bp = payload["blueprints"][0]
    assert bp["id"] == "demo_bp"
    assert bp["name"] == "DemoBP"
    assert bp["required_mcp_servers"] == ["filesystem", "mcp-shell"]
    comp = bp["compliance"]

    # mcp-shell missing, filesystem present but unresolved env → partial/missing
    assert comp["missing_servers"] == ["mcp-shell"]
    # With one missing server, status should be 'missing'
    assert comp["status"] in ("missing", "partial")
    # Check unresolved env aggregation contains ALLOWED_PATH
    assert "ALLOWED_PATH" in comp.get("unresolved_env", [])
