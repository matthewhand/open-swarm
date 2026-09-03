"""GET /v1/support/context/ — live briefing payload."""

from unittest.mock import patch

from rest_framework import status


def test_support_context_endpoint(api_client):
    fake = {
        "agents": [{"id": "support", "name": "Support", "role": "support"}],
        "agent_count": 1,
        "inference": {"configured": False, "profiles": [], "env_signals": []},
        "create": {"team": "/teams/launch/", "settings": "/settings/"},
        "chips": {},
    }
    briefing = "**Agents**\n- Support · support\n\n**Inference** off"
    with patch("swarm.core.support_context.live_context", return_value=fake):
        with patch(
            "swarm.core.support_context.briefing_markdown",
            return_value=briefing,
        ):
            response = api_client.get("/v1/support/context/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["object"] == "support.context"
    assert body["briefing"] == briefing
    assert body["welcome"] == briefing
    assert "[New team]" not in body["briefing"]
    assert body["inference"]["configured"] is False
