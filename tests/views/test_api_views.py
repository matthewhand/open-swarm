"""
Unit tests for src/swarm/views/api_views.py
===========================================

Tests for API views covering:
- ModelsListView: list models (blueprints) in OpenAI format
- BlueprintsListView: list blueprints with metadata and filters
- CustomBlueprintsView: CRUD for user custom blueprints
- CustomBlueprintDetailView: GET/PATCH/DELETE for single blueprint
- Marketplace views: return empty list when Wagtail disabled

Uses mocks for blueprint discovery and external calls; no network.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def mock_blueprints_dict():
    """Sample blueprints returned as dict with metadata."""
    return {
        "assistant": {
            "metadata": {
                "name": "Assistant",
                "description": "General assistant blueprint",
                "abbreviation": "AST",
                "required_mcp_servers": ["filesystem"],
                "tags": ["general", "assistant"],
            }
        },
        "developer": {
            "metadata": {
                "name": "Developer",
                "description": "Code development blueprint",
                "abbreviation": "DEV",
                "required_mcp_servers": ["github", "filesystem"],
                "tags": ["code", "development"],
            }
        },
        "simple_agent": {
            "metadata": {
                "name": "Simple Agent",
                "description": "Minimal agent with no MCP requirements",
                "required_mcp_servers": [],
                "tags": ["simple"],
            }
        },
    }


@pytest.fixture
def mock_blueprints_list():
    """Sample blueprints returned as list (legacy format)."""
    return ["assistant", "developer", "simple_agent"]


@pytest.fixture
def mock_custom_blueprints():
    """Sample custom blueprints in library."""
    return [
        {
            "id": "my_custom_agent",
            "name": "My Custom Agent",
            "description": "A custom agent for testing",
            "category": "ai_assistants",
            "tags": ["custom", "test"],
            "requirements": "",
            "code": "# custom code",
            "required_mcp_servers": [],
            "env_vars": [],
        },
        {
            "id": "another_agent",
            "name": "Another Agent",
            "description": "Another test agent",
            "category": "utilities",
            "tags": ["utility"],
            "requirements": "",
            "code": "# another code",
            "required_mcp_servers": ["filesystem"],
            "env_vars": ["API_KEY"],
        },
    ]


@pytest.fixture
def mock_blueprint_library(mock_custom_blueprints):
    """Mock blueprint library structure."""
    return {
        "installed": ["assistant", "developer"],
        "custom": mock_custom_blueprints,
    }


# =============================================================================
# Tests for ModelsListView
# =============================================================================

class TestModelsListView:
    """Tests for /v1/models endpoint."""

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_models_with_dict_response(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test listing models when blueprints returned as dict."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 3
        model_ids = [m["id"] for m in data["data"]]
        assert "assistant" in model_ids
        assert "developer" in model_ids
        assert "simple_agent" in model_ids
        for model in data["data"]:
            assert model["object"] == "model"
            assert "created" in model
            assert model["owned_by"] == "open-swarm"

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_models_with_list_response(
        self, mock_get_blueprints, api_client, mock_blueprints_list
    ):
        """Test listing models when blueprints returned as list."""
        mock_get_blueprints.return_value = mock_blueprints_list

        response = api_client.get("/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 3

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_models_empty(self, mock_get_blueprints, api_client):
        """Test listing models when no blueprints available."""
        mock_get_blueprints.return_value = {}

        response = api_client.get("/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 0

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_models_unexpected_type(self, mock_get_blueprints, api_client):
        """Test listing models handles unexpected return type gracefully."""
        mock_get_blueprints.return_value = "invalid_type"

        response = api_client.get("/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 0

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_models_error(self, mock_get_blueprints, api_client):
        """Test listing models handles exceptions gracefully."""
        mock_get_blueprints.side_effect = Exception("Database error")

        response = api_client.get("/v1/models/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data


# =============================================================================
# Tests for BlueprintsListView
# =============================================================================

class TestBlueprintsListView:
    """Tests for /v1/blueprints endpoint."""

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_basic(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test listing blueprints with basic metadata."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 3

        # Check first blueprint structure
        bp = data["data"][0]
        assert "id" in bp
        assert "name" in bp
        assert "description" in bp
        assert "required_mcp_servers" in bp
        assert "tags" in bp

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_search_filter(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test listing blueprints with search filter."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/?search=developer")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should match "developer" in id or name
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "developer"

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_search_by_description(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test search filter matches description."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/?search=general")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should match "general" in assistant description
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "assistant"

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_required_mcp_filter(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test listing blueprints filtered by required MCP server."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/?required_mcp=github")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Only developer requires github
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "developer"

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_combined_filters(
        self, mock_get_blueprints, api_client, mock_blueprints_dict
    ):
        """Test listing blueprints with combined filters."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/?search=dev&required_mcp=github")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "developer"

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_no_match(self, mock_get_blueprints, api_client, mock_blueprints_dict):
        """Test listing blueprints when filter matches nothing."""
        mock_get_blueprints.return_value = mock_blueprints_dict

        response = api_client.get("/v1/blueprints/?search=nonexistent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 0

    @patch("swarm.views.api_views.get_available_blueprints")
    def test_list_blueprints_error(self, mock_get_blueprints, api_client):
        """Test listing blueprints handles exceptions gracefully."""
        mock_get_blueprints.side_effect = Exception("Discovery error")

        response = api_client.get("/v1/blueprints/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data


# =============================================================================
# Tests for CustomBlueprintsView
# =============================================================================

class TestCustomBlueprintsView:
    """Tests for /v1/blueprints/custom/ endpoint."""

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_list_custom_blueprints(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test listing custom blueprints."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_list_custom_blueprints_search_filter(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test listing custom blueprints with search filter."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/?search=another")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "another_agent"

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_list_custom_blueprints_tag_filter(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test listing custom blueprints with tag filter."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/?tag=utility")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "another_agent"

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_list_custom_blueprints_category_filter(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test listing custom blueprints with category filter."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/?category=utilities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "another_agent"

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_list_custom_blueprints_empty(self, mock_get_library, api_client):
        """Test listing custom blueprints when empty."""
        mock_get_library.return_value = {"installed": [], "custom": []}

        response = api_client.get("/v1/blueprints/custom/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 0

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_create_custom_blueprint(
        self, mock_get_library, mock_save_library, api_client
    ):
        """Test creating a new custom blueprint."""
        mock_get_library.return_value = {"installed": [], "custom": []}
        mock_save_library.return_value = True

        payload = {
            "name": "New Agent",
            "description": "A new test agent",
            "category": "test",
            "tags": ["new"],
            "code": "# new code",
        }

        response = api_client.post("/v1/blueprints/custom/", data=payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "new_agent"
        assert data["name"] == "New Agent"
        assert data["description"] == "A new test agent"

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_create_custom_blueprint_with_id(
        self, mock_get_library, mock_save_library, api_client
    ):
        """Test creating a custom blueprint with explicit ID."""
        mock_get_library.return_value = {"installed": [], "custom": []}
        mock_save_library.return_value = True

        payload = {
            "id": "my_special_id",
            "name": "Special Agent",
            "description": "Agent with explicit ID",
        }

        response = api_client.post("/v1/blueprints/custom/", data=payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "my_special_id"

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_create_custom_blueprint_missing_id(
        self, mock_get_library, api_client
    ):
        """Test creating a custom blueprint without ID returns error."""
        mock_get_library.return_value = {"installed": [], "custom": []}

        payload = {"description": "No ID provided"}

        response = api_client.post("/v1/blueprints/custom/", data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_create_custom_blueprint_duplicate_id(
        self, mock_get_library, api_client, mock_custom_blueprints
    ):
        """Test creating a custom blueprint with duplicate ID returns error."""
        mock_get_library.return_value = {"installed": [], "custom": mock_custom_blueprints}

        payload = {
            "id": "my_custom_agent",
            "name": "Duplicate Agent",
        }

        response = api_client.post("/v1/blueprints/custom/", data=payload, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "error" in data

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_create_custom_blueprint_save_failure(
        self, mock_get_library, mock_save_library, api_client
    ):
        """Test creating a custom blueprint when save fails."""
        mock_get_library.return_value = {"installed": [], "custom": []}
        mock_save_library.return_value = False

        payload = {"name": "Test Agent"}

        response = api_client.post("/v1/blueprints/custom/", data=payload, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Tests for CustomBlueprintDetailView
# =============================================================================

class TestCustomBlueprintDetailView:
    """Tests for /v1/blueprints/custom/<id>/ endpoint."""

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_get_custom_blueprint(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test getting a single custom blueprint."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/my_custom_agent/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "my_custom_agent"
        assert data["name"] == "My Custom Agent"

    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_get_custom_blueprint_not_found(
        self, mock_get_library, api_client, mock_blueprint_library
    ):
        """Test getting a non-existent custom blueprint."""
        mock_get_library.return_value = mock_blueprint_library

        response = api_client.get("/v1/blueprints/custom/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_delete_custom_blueprint(
        self, mock_get_library, mock_save_library, api_client, mock_blueprint_library
    ):
        """Test deleting a custom blueprint."""
        mock_get_library.return_value = mock_blueprint_library
        mock_save_library.return_value = True

        response = api_client.delete("/v1/blueprints/custom/my_custom_agent/")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_delete_custom_blueprint_not_found(
        self, mock_get_library, mock_save_library, api_client, mock_blueprint_library
    ):
        """Test deleting a non-existent custom blueprint returns 204."""
        mock_get_library.return_value = mock_blueprint_library
        mock_save_library.return_value = True

        response = api_client.delete("/v1/blueprints/custom/nonexistent/")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_patch_custom_blueprint(
        self, mock_get_library, mock_save_library, api_client, mock_blueprint_library
    ):
        """Test updating a custom blueprint with PATCH."""
        mock_get_library.return_value = mock_blueprint_library
        mock_save_library.return_value = True

        payload = {
            "name": "Updated Agent",
            "description": "Updated description",
        }

        response = api_client.patch(
            "/v1/blueprints/custom/my_custom_agent/", data=payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Agent"
        assert data["description"] == "Updated description"

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_patch_custom_blueprint_not_found(
        self, mock_get_library, mock_save_library, api_client, mock_blueprint_library
    ):
        """Test updating a non-existent custom blueprint."""
        mock_get_library.return_value = mock_blueprint_library
        mock_save_library.return_value = True

        payload = {"name": "Updated"}

        response = api_client.patch(
            "/v1/blueprints/custom/nonexistent/", data=payload, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("swarm.views.api_views.save_user_blueprint_library")
    @patch("swarm.views.api_views.get_user_blueprint_library")
    def test_put_custom_blueprint(
        self, mock_get_library, mock_save_library, api_client, mock_blueprint_library
    ):
        """Test updating a custom blueprint with PUT (alias for PATCH)."""
        mock_get_library.return_value = mock_blueprint_library
        mock_save_library.return_value = True

        payload = {"name": "PUT Updated"}

        response = api_client.put(
            "/v1/blueprints/custom/my_custom_agent/", data=payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "PUT Updated"


# =============================================================================
# Tests for Marketplace Views
# =============================================================================

class TestMarketplaceBlueprintsView:
    """Tests for /marketplace/blueprints/ endpoint."""

    def test_list_marketplace_blueprints_disabled(self, api_client):
        """Test marketplace blueprints returns empty when Wagtail disabled."""
        response = api_client.get("/marketplace/blueprints/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"object": "list", "data": []}


class TestMarketplaceMCPConfigsView:
    """Tests for /marketplace/mcp-configs/ endpoint."""

    def test_list_marketplace_mcp_configs_disabled(self, api_client):
        """Test marketplace MCP configs returns empty when Wagtail disabled."""
        response = api_client.get("/marketplace/mcp-configs/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"object": "list", "data": []}


class TestMarketplaceGitHubBlueprintsView:
    """Tests for /marketplace/github/blueprints/ endpoint."""

    @patch("swarm.views.api_views.ENABLE_GITHUB_MARKETPLACE", False)
    def test_list_github_blueprints_disabled(self, api_client):
        """Test GitHub blueprints returns empty when feature disabled."""
        response = api_client.get("/marketplace/github/blueprints/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"object": "list", "data": []}


class TestMarketplaceGitHubMCPConfigsView:
    """Tests for /marketplace/github/mcp-configs/ endpoint."""

    @patch("swarm.views.api_views.ENABLE_GITHUB_MARKETPLACE", False)
    def test_list_github_mcp_configs_disabled(self, api_client):
        """Test GitHub MCP configs returns empty when feature disabled."""
        response = api_client.get("/marketplace/github/mcp-configs/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == {"object": "list", "data": []}
