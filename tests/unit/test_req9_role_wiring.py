"""REQ-9 contracts: codegen wiring, sidepane class names, API role fields."""

from pathlib import Path
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from swarm.core.agent_roles import ROLE_CSS_CLASSES
from swarm.views.agent_creator_views import _render_swarm_blueprint_code

REPO = Path(__file__).resolve().parents[2]
DJANGO_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
SPA_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
SIDEBAR_TS = REPO / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
TEAM_JS = REPO / "src" / "swarm" / "static" / "js" / "team_creator.js"


def _team(*, gate=False, skeptic=False):
    agents = [
        {"name": "Writer", "system_prompt": "You write files.", "role": "default"},
        {"name": "Editor", "system_prompt": "You edit.", "role": "default"},
    ]
    if gate:
        agents.append({
            "name": "ToolGate",
            "role": "gate",
            "system_prompt": "Classify tool calls.",
        })
    if skeptic:
        agents.append({
            "name": "Skeptic",
            "role": "skeptic",
            "system_prompt": "Review whether work landed.",
        })
    return {
        "name": "Role Team",
        "description": "REQ-9 wiring fixture",
        "coordinator_name": "Writer",
        "agents": agents,
    }


def test_codegen_unwired_still_calls_wrap_but_gate_is_none():
    code = _render_swarm_blueprint_code(_team())
    assert "wrap_tools_with_gate" in code
    assert "run_with_skeptic" in code
    assert "find_role_agent(self._agents, \"gate\")" in code
    assert "find_role_agent(self._agents, \"skeptic\")" in code
    assert '"role": \'default\'' in code or '"role": "default"' in code


def test_codegen_wires_gate_and_skeptic_roles():
    code = _render_swarm_blueprint_code(_team(gate=True, skeptic=True))
    assert "attach_gate_as_tool" in code
    assert "attach_skeptic_as_tool" in code
    assert '"role": \'gate\'' in code or '"role": "gate"' in code
    assert '"role": \'skeptic\'' in code or '"role": "skeptic"' in code
    assert "gate_agent" in code
    assert "skeptic_agent" in code
    assert "single token" in code.lower() or "Classify" in code


def test_sidepane_css_class_names_exist_django_and_spa():
    django_css = DJANGO_CSS.read_text(encoding="utf-8")
    spa_css = SPA_CSS.read_text(encoding="utf-8")
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    ts = SIDEBAR_TS.read_text(encoding="utf-8")
    team = TEAM_JS.read_text(encoding="utf-8")
    for role, css_class in ROLE_CSS_CLASSES.items():
        if role == "default":
            continue
        assert css_class in django_css
        assert css_class in spa_css
        assert f'data-role="{role}"' in django_css or f'data-role="{role}"' in spa_css
    assert "data-role" in js
    assert "os-agent-role-" in js
    assert "os-agent-role-${role}" in ts or "os-agent-role-" in ts
    assert "member-agent-role" in team
    assert 'value="gate"' in team
    assert 'value="skeptic"' in team
    assert 'value="support"' in team


@pytest.mark.django_db
def test_blueprints_list_includes_role_fields():
    client = APIClient()
    payload = {
        "support_bot": {
            "metadata": {
                "name": "Support",
                "description": "Onboard help",
                "role": "support",
                "tags": [],
                "required_mcp_servers": [],
                "agents": [{"name": "Support", "role": "support"}],
            }
        },
        "plain": {
            "metadata": {
                "name": "Plain",
                "description": "No special role",
                "tags": [],
                "required_mcp_servers": [],
            }
        },
    }
    with patch("swarm.views.api_views.get_available_blueprints", return_value=payload):
        response = client.get("/v1/blueprints/")
    assert response.status_code == status.HTTP_200_OK
    by_id = {row["id"]: row for row in response.json()["data"]}
    assert by_id["support_bot"]["role"] == "support"
    assert by_id["support_bot"]["agents"][0]["role"] == "support"
    assert by_id["plain"]["role"] == "default"
    assert by_id["plain"]["gate_agent"] is None
    assert by_id["plain"]["skeptic_agent"] is None
