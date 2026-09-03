"""GET /v1/support/context/ — live welcome payload."""

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
    with patch("swarm.core.support_context.live_context", return_value=fake):
        with patch(
            "swarm.core.support_context.welcome_markdown",
            return_value="**Support**\n\n[New team](/teams/launch/)",
        ):
            response = api_client.get("/v1/support/context/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["object"] == "support.context"
    assert body["welcome"].startswith("**Support**")
    assert "[New team](/teams/launch/)" in body["welcome"]
    assert body["inference"]["configured"] is False
