"""
Unit tests for src/swarm/views/teams_api.py
===========================================

Tests for the JSON Teams API (ROADMAP 3.1) covering:
- TeamsAPIView GET  /v1/teams/        : list teams in OpenAI-style envelope
- TeamsAPIView POST /v1/teams/        : create (slugify, validation, conflicts)
- TeamDetailAPIView DELETE /v1/teams/<id>/ : delete + 404 behaviour
- Auth behaviour with HasValidTokenOrSession (token / session / anonymous)

The dynamic-team registry helpers are mocked so no real teams.json on disk is
read or written.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from swarm.permissions import HasValidTokenOrSession
from swarm.views.teams_api import TeamDetailAPIView, TeamsAPIView


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def mock_registry():
    """Sample dynamic-team registry as stored in teams.json."""
    return {
        "research-team": {
            "id": "research-team",
            "description": "Research helpers",
            "llm_profile": "default",
        },
        "ops-team": {
            "id": "ops-team",
            "description": "Operations crew",
            "llm_profile": "qwen3.5",
        },
    }


# =============================================================================
# Tests for GET /v1/teams/
# =============================================================================

class TestTeamsListView:
    """Tests for listing teams."""

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_list_teams(self, mock_load, api_client, mock_registry):
        """Teams are returned in an OpenAI-style list envelope."""
        mock_load.return_value = mock_registry

        response = api_client.get("/v1/teams/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        ids = [t["id"] for t in data["data"]]
        assert "research-team" in ids
        assert "ops-team" in ids
        for team in data["data"]:
            assert team["object"] == "team"
            assert "description" in team
            assert "llm_profile" in team

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_list_teams_empty(self, mock_load, api_client):
        """Empty registry yields an empty list envelope."""
        mock_load.return_value = {}

        response = api_client.get("/v1/teams/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"object": "list", "data": []}

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_list_teams_no_trailing_slash(self, mock_load, api_client, mock_registry):
        """The endpoint is reachable without a trailing slash too."""
        mock_load.return_value = mock_registry

        response = api_client.get("/v1/teams")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["object"] == "list"

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_list_teams_error(self, mock_load, api_client):
        """Registry errors surface as a 500 with an error body."""
        mock_load.side_effect = Exception("disk error")

        response = api_client.get("/v1/teams/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()


# =============================================================================
# Tests for POST /v1/teams/
# =============================================================================

class TestTeamsCreateView:
    """Tests for creating teams."""

    @patch("swarm.views.teams_api.register_dynamic_team")
    @patch("swarm.views.teams_api.discover_blueprints")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team(self, mock_load, mock_discover, mock_register, api_client):
        """A valid create registers the team and returns 201 with the team."""
        mock_load.return_value = {}
        mock_discover.return_value = {}

        payload = {
            "name": "My Team",
            "description": "A test team",
            "llm_profile": "default",
        }
        response = api_client.post("/v1/teams/", data=payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "my-team"
        assert data["object"] == "team"
        assert data["description"] == "A test team"
        assert data["llm_profile"] == "default"
        mock_register.assert_called_once_with(
            "my-team", description="A test team", llm_profile="default"
        )

    @patch("swarm.views.teams_api.register_dynamic_team")
    @patch("swarm.views.teams_api.discover_blueprints")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_slugifies_name(
        self, mock_load, mock_discover, mock_register, api_client
    ):
        """Names are slugified the same way as the /teams/ admin form."""
        mock_load.return_value = {}
        mock_discover.return_value = {}

        response = api_client.post(
            "/v1/teams/", data={"name": "  Alpha & Beta Team!  "}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] == "alpha---beta-team"
        mock_register.assert_called_once_with(
            "alpha---beta-team", description=None, llm_profile=None
        )

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_missing_name(self, mock_load, api_client):
        """Missing name returns 400."""
        mock_load.return_value = {}

        response = api_client.post("/v1/teams/", data={}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_invalid_name(self, mock_load, api_client):
        """A name with no alphanumerics returns 400."""
        mock_load.return_value = {}

        response = api_client.post("/v1/teams/", data={"name": "!!!"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_name_too_long(self, mock_load, api_client):
        """A slug longer than 64 characters returns 400."""
        mock_load.return_value = {}

        response = api_client.post(
            "/v1/teams/", data={"name": "x" * 65}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_duplicate(self, mock_load, api_client, mock_registry):
        """Creating a team whose slug already exists returns 409."""
        mock_load.return_value = mock_registry

        response = api_client.post(
            "/v1/teams/", data={"name": "Research Team"}, format="json"
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "error" in response.json()

    @patch("swarm.views.teams_api.discover_blueprints")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_blueprint_collision(
        self, mock_load, mock_discover, api_client
    ):
        """A slug colliding with a static blueprint returns 409."""
        mock_load.return_value = {}
        mock_discover.return_value = {"jeeves": {"metadata": {}}}

        response = api_client.post(
            "/v1/teams/", data={"name": "Jeeves"}, format="json"
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "error" in response.json()

    @patch("swarm.views.teams_api.register_dynamic_team")
    @patch("swarm.views.teams_api.discover_blueprints")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_create_team_discovery_failure_is_nonfatal(
        self, mock_load, mock_discover, mock_register, api_client
    ):
        """Blueprint discovery errors do not block team creation."""
        mock_load.return_value = {}
        mock_discover.side_effect = Exception("discovery exploded")

        response = api_client.post(
            "/v1/teams/", data={"name": "resilient"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        mock_register.assert_called_once()


# =============================================================================
# Tests for DELETE /v1/teams/<id>/
# =============================================================================

class TestTeamDetailView:
    """Tests for deleting teams."""

    @patch("swarm.views.teams_api.deregister_dynamic_team")
    def test_delete_team(self, mock_deregister, api_client):
        """Deleting an existing team returns 204."""
        mock_deregister.return_value = True

        response = api_client.delete("/v1/teams/research-team/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_deregister.assert_called_once_with("research-team")

    @patch("swarm.views.teams_api.deregister_dynamic_team")
    def test_delete_team_not_found(self, mock_deregister, api_client):
        """Deleting an unknown team returns 404."""
        mock_deregister.return_value = False

        response = api_client.delete("/v1/teams/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.json()

    @patch("swarm.views.teams_api.deregister_dynamic_team")
    def test_delete_team_error(self, mock_deregister, api_client):
        """Registry errors surface as a 500."""
        mock_deregister.side_effect = Exception("disk error")

        response = api_client.delete("/v1/teams/research-team/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Tests for authentication behaviour
# =============================================================================

class TestTeamsAPIAuth:
    """Auth behaviour for the teams endpoints.

    The views resolve their permission classes from ENABLE_API_AUTH at import
    time (mirroring REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES). These tests
    pin the hardened permission class explicitly to exercise both outcomes.
    """

    def _authed_user(self):
        user = MagicMock()
        user.is_authenticated = True
        return user

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_disabled_allows_anonymous(self, mock_load, api_client):
        """With auth disabled (no API token configured), anonymous access works.

        This matches /v1/blueprints/ behaviour in unauthenticated deployments.
        """
        mock_load.return_value = {}
        with patch.object(TeamsAPIView, "permission_classes", []):
            response = api_client.get("/v1/teams/")
        assert response.status_code == status.HTTP_200_OK

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_enabled_rejects_anonymous(self, mock_load, api_client):
        """With HasValidTokenOrSession enforced, anonymous requests are denied."""
        mock_load.return_value = {}
        with patch.object(
            TeamsAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/teams/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_enabled_rejects_anonymous_delete(self, mock_load, api_client):
        """Mutating endpoints are denied for anonymous callers too."""
        mock_load.return_value = {}
        with patch.object(
            TeamDetailAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.delete("/v1/teams/anything/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @override_settings(SWARM_API_KEY="test-token-123")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_enabled_accepts_valid_bearer_token(self, mock_load, api_client):
        """A valid static Bearer token grants access."""
        mock_load.return_value = {}
        api_client.credentials(HTTP_AUTHORIZATION="Bearer test-token-123")
        with patch.object(
            TeamsAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/teams/")
        assert response.status_code == status.HTTP_200_OK

    @override_settings(SWARM_API_KEY="test-token-123")
    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_enabled_rejects_invalid_bearer_token(self, mock_load, api_client):
        """An invalid static Bearer token is rejected."""
        mock_load.return_value = {}
        api_client.credentials(HTTP_AUTHORIZATION="Bearer wrong-token")
        with patch.object(
            TeamsAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/teams/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("swarm.views.teams_api.load_dynamic_registry")
    def test_auth_enabled_accepts_session_user(self, mock_load, api_client):
        """An authenticated session user grants access."""
        mock_load.return_value = {}
        api_client.force_authenticate(user=self._authed_user())
        with patch.object(
            TeamsAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/teams/")
        assert response.status_code == status.HTTP_200_OK
