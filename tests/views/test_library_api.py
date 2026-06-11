"""
Unit tests for src/swarm/views/library_api.py
=============================================

Tests for the JSON Blueprint Library API covering:
- LibraryAPIView GET  /v1/library/        : list library in OpenAI-style envelope
- LibraryAPIView POST /v1/library/        : add (validation, idempotency, 404)
- LibraryDetailAPIView DELETE /v1/library/<name>/ : remove + 404 behaviour
- Auth behaviour with HasValidTokenOrSession (token / session / anonymous)

The file-backed library helpers are mocked so no real blueprint_library.json
on disk is read or written.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from swarm.permissions import HasValidTokenOrSession
from swarm.views.library_api import LibraryAPIView, LibraryDetailAPIView


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def mock_library():
    """Sample library as stored in blueprint_library.json."""
    return {"installed": ["codey", "poets"], "custom": []}


# =============================================================================
# Tests for GET /v1/library/
# =============================================================================

class TestLibraryListView:
    """Tests for listing the user's blueprint library."""

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library(self, mock_get, api_client, mock_library):
        """Library entries are returned in an OpenAI-style list envelope."""
        mock_get.return_value = mock_library

        response = api_client.get("/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        ids = [e["id"] for e in data["data"]]
        assert ids == ["codey", "poets"]
        for entry in data["data"]:
            assert entry["object"] == "library.blueprint"
            assert "name" in entry
            assert "description" in entry

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library_known_metadata(self, mock_get, api_client, mock_library):
        """Entries reuse the Django pages' curated metadata when available."""
        mock_get.return_value = mock_library

        response = api_client.get("/v1/library/")

        codey = response.json()["data"][0]
        assert codey["name"] == "Codey"
        assert "coding" in codey["description"].lower()

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library_unknown_metadata_fallback(self, mock_get, api_client):
        """Unknown blueprints get the same title-cased fallback as the Django UI."""
        mock_get.return_value = {"installed": ["my_custom_thing"], "custom": []}

        response = api_client.get("/v1/library/")

        entry = response.json()["data"][0]
        assert entry["name"] == "My Custom Thing"
        assert entry["description"] == "Blueprint for my_custom_thing"

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library_empty(self, mock_get, api_client):
        """An empty library yields an empty list envelope."""
        mock_get.return_value = {"installed": [], "custom": []}

        response = api_client.get("/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"object": "list", "data": []}

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library_no_trailing_slash(self, mock_get, api_client, mock_library):
        """The endpoint is reachable without a trailing slash too."""
        mock_get.return_value = mock_library

        response = api_client.get("/v1/library")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["object"] == "list"

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_list_library_error(self, mock_get, api_client):
        """Storage errors surface as a 500 with an error body."""
        mock_get.side_effect = Exception("disk error")

        response = api_client.get("/v1/library/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()


# =============================================================================
# Tests for POST /v1/library/
# =============================================================================

class TestLibraryAddView:
    """Tests for adding blueprints to the library."""

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint(self, mock_discover, mock_get, mock_save, api_client):
        """A valid add persists the blueprint and returns 201 with the entry."""
        mock_discover.return_value = {"codey": {"metadata": {}}}
        mock_get.return_value = {"installed": [], "custom": []}
        mock_save.return_value = True

        response = api_client.post(
            "/v1/library/", data={"name": "codey"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "codey"
        assert data["object"] == "library.blueprint"
        mock_save.assert_called_once_with({"installed": ["codey"], "custom": []})

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint_accepts_id_key(
        self, mock_discover, mock_get, mock_save, api_client
    ):
        """The body may use "id" instead of "name" (matching /v1/teams/)."""
        mock_discover.return_value = {"poets": {"metadata": {}}}
        mock_get.return_value = {"installed": [], "custom": []}
        mock_save.return_value = True

        response = api_client.post(
            "/v1/library/", data={"id": "poets"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] == "poets"

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint_already_in_library(
        self, mock_discover, mock_get, mock_save, api_client, mock_library
    ):
        """Adding a blueprint already in the library is idempotent (200, no save)."""
        mock_discover.return_value = {"codey": {"metadata": {}}}
        mock_get.return_value = mock_library

        response = api_client.post(
            "/v1/library/", data={"name": "codey"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == "codey"
        mock_save.assert_not_called()

    def test_add_blueprint_missing_name(self, api_client):
        """Missing name returns 400."""
        response = api_client.post("/v1/library/", data={}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint_unknown(self, mock_discover, api_client):
        """Adding a blueprint that isn't discovered on the server returns 404."""
        mock_discover.return_value = {"codey": {"metadata": {}}}

        response = api_client.post(
            "/v1/library/", data={"name": "nonexistent"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.json()

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint_save_failure(
        self, mock_discover, mock_get, mock_save, api_client
    ):
        """A failed save surfaces as a 500."""
        mock_discover.return_value = {"codey": {"metadata": {}}}
        mock_get.return_value = {"installed": [], "custom": []}
        mock_save.return_value = False

        response = api_client.post(
            "/v1/library/", data={"name": "codey"}, format="json"
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()

    @patch("swarm.views.library_api.discover_blueprints")
    def test_add_blueprint_discovery_error(self, mock_discover, api_client):
        """Discovery errors surface as a 500."""
        mock_discover.side_effect = Exception("discovery exploded")

        response = api_client.post(
            "/v1/library/", data={"name": "codey"}, format="json"
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Tests for DELETE /v1/library/<name>/
# =============================================================================

class TestLibraryRemoveView:
    """Tests for removing blueprints from the library."""

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_remove_blueprint(self, mock_get, mock_save, api_client, mock_library):
        """Removing a blueprint in the library returns 204 and persists."""
        mock_get.return_value = mock_library
        mock_save.return_value = True

        response = api_client.delete("/v1/library/codey/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_save.assert_called_once_with({"installed": ["poets"], "custom": []})

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_remove_blueprint_not_in_library(self, mock_get, api_client, mock_library):
        """Removing a blueprint not in the library returns 404."""
        mock_get.return_value = mock_library

        response = api_client.delete("/v1/library/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.json()

    @patch("swarm.views.library_api.save_user_blueprint_library")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_remove_blueprint_save_failure(
        self, mock_get, mock_save, api_client, mock_library
    ):
        """A failed save surfaces as a 500."""
        mock_get.return_value = mock_library
        mock_save.return_value = False

        response = api_client.delete("/v1/library/codey/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_remove_blueprint_error(self, mock_get, api_client):
        """Storage errors surface as a 500."""
        mock_get.side_effect = Exception("disk error")

        response = api_client.delete("/v1/library/codey/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Tests for authentication behaviour
# =============================================================================

class TestLibraryAPIAuth:
    """Auth behaviour for the library endpoints.

    The views resolve their permission classes from ENABLE_API_AUTH at import
    time (mirroring REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES). These tests
    pin the hardened permission class explicitly to exercise both outcomes.
    """

    def _authed_user(self):
        user = MagicMock()
        user.is_authenticated = True
        return user

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_disabled_allows_anonymous(self, mock_get, api_client):
        """With auth disabled (no API token configured), anonymous access works."""
        mock_get.return_value = {"installed": [], "custom": []}
        with patch.object(LibraryAPIView, "permission_classes", []):
            response = api_client.get("/v1/library/")
        assert response.status_code == status.HTTP_200_OK

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_enabled_rejects_anonymous(self, mock_get, api_client):
        """With HasValidTokenOrSession enforced, anonymous requests are denied."""
        mock_get.return_value = {"installed": [], "custom": []}
        with patch.object(
            LibraryAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/library/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_enabled_rejects_anonymous_delete(self, mock_get, api_client):
        """Mutating endpoints are denied for anonymous callers too."""
        mock_get.return_value = {"installed": [], "custom": []}
        with patch.object(
            LibraryDetailAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.delete("/v1/library/anything/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @override_settings(SWARM_API_KEY="test-token-123")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_enabled_accepts_valid_bearer_token(self, mock_get, api_client):
        """A valid static Bearer token grants access."""
        mock_get.return_value = {"installed": [], "custom": []}
        api_client.credentials(HTTP_AUTHORIZATION="Bearer test-token-123")
        with patch.object(
            LibraryAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/library/")
        assert response.status_code == status.HTTP_200_OK

    @override_settings(SWARM_API_KEY="test-token-123")
    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_enabled_rejects_invalid_bearer_token(self, mock_get, api_client):
        """An invalid static Bearer token is rejected."""
        mock_get.return_value = {"installed": [], "custom": []}
        api_client.credentials(HTTP_AUTHORIZATION="Bearer wrong-token")
        with patch.object(
            LibraryAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/library/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("swarm.views.library_api.get_user_blueprint_library")
    def test_auth_enabled_accepts_session_user(self, mock_get, api_client):
        """An authenticated session user grants access."""
        mock_get.return_value = {"installed": [], "custom": []}
        api_client.force_authenticate(user=self._authed_user())
        with patch.object(
            LibraryAPIView, "permission_classes", [HasValidTokenOrSession]
        ):
            response = api_client.get("/v1/library/")
        assert response.status_code == status.HTTP_200_OK
