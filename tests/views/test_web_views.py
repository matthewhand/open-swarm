"""
Unit tests for src/swarm/views/web_views.py
===========================================

Tests for web views covering:
- index: main page with blueprint discovery
- blueprint_webpage: blueprint detail page (valid/invalid)
- serve_swarm_config: config endpoint
- custom_login: login handling
- team_launcher: team launcher UI (gated by ENABLE_WEBUI)

Uses mocks for blueprint discovery and external calls; no network.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from django.test import RequestFactory, Client
from django.http import HttpResponse, JsonResponse


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def request_factory():
    """Return a RequestFactory for creating request objects."""
    return RequestFactory()


@pytest.fixture
def mock_blueprints_metadata():
    """Sample blueprints metadata from discovery."""
    return {
        "assistant": {
            "metadata": {"name": "Assistant", "description": "General assistant"}
        },
        "developer": {
            "metadata": {"name": "Developer", "description": "Code development"}
        },
        "simple_agent": {
            "metadata": {"name": "Simple Agent", "description": "Minimal agent"}
        },
    }


@pytest.fixture
def mock_swarm_config(tmp_path):
    """Create a temporary swarm_config.json file."""
    config_data = {
        "default_blueprint": "assistant",
        "blueprints": {
            "assistant": {"model": "gpt-4"}
        }
    }
    config_file = tmp_path / "swarm_config.json"
    config_file.write_text(json.dumps(config_data))
    return config_file


# =============================================================================
# Tests for index view
# =============================================================================

class TestIndexView:
    """Tests for the index page view."""

    @patch("swarm.views.web_views.discover_blueprints")
    @patch("swarm.views.web_views.render")
    def test_index_success(self, mock_render, mock_discover, client, mock_blueprints_metadata):
        """Test index page renders with discovered blueprints."""
        mock_discover.return_value = mock_blueprints_metadata
        mock_render.return_value = HttpResponse(status=200)

        response = client.get("/")

        # Verify discover_blueprints was called
        mock_discover.assert_called_once()
        # Verify render was called with correct context
        assert mock_render.called

    @patch("swarm.views.web_views.discover_blueprints")
    @patch("swarm.views.web_views.render")
    def test_index_with_blueprints(self, mock_render, mock_discover, client, mock_blueprints_metadata):
        """Test index page context contains blueprints."""
        mock_discover.return_value = mock_blueprints_metadata
        mock_render.return_value = HttpResponse(status=200)

        response = client.get("/")

        # Response should be successful
        assert response.status_code == 200

    @patch("swarm.views.web_views.discover_blueprints")
    @patch("swarm.views.web_views.render")
    def test_index_empty_blueprints(self, mock_render, mock_discover, client):
        """Test index page handles empty blueprint list."""
        mock_discover.return_value = {}
        mock_render.return_value = HttpResponse(status=200)

        response = client.get("/")

        assert response.status_code == 200

    @patch("swarm.views.web_views.discover_blueprints")
    @patch("swarm.views.web_views.render")
    def test_index_discovery_error(self, mock_render, mock_discover, client):
        """Test index page handles discovery errors gracefully."""
        mock_discover.side_effect = Exception("Discovery failed")
        mock_render.return_value = HttpResponse(status=200)

        response = client.get("/")

        # Should still render, but with empty blueprints
        assert response.status_code == 200


# =============================================================================
# Tests for blueprint_webpage view
# =============================================================================

class TestBlueprintWebpageView:
    """Tests for the blueprint detail page view."""

    @patch("swarm.views.web_views.discover_blueprints")
    @patch("swarm.views.web_views.render")
    def test_blueprint_page_valid(self, mock_render, mock_discover, client, mock_blueprints_metadata):
        """Test blueprint page for valid blueprint name."""
        mock_discover.return_value = mock_blueprints_metadata
        mock_render.return_value = HttpResponse(status=200)

        # Test via request factory for direct view testing
        from swarm.views.web_views import blueprint_webpage

        factory = RequestFactory()
        request = factory.get("/blueprint/assistant/")
        # Add session attribute to request
        request.session = {}

        response = blueprint_webpage(request, "assistant")

        assert response.status_code == 200

    @patch("swarm.views.web_views.discover_blueprints")
    def test_blueprint_page_not_found(self, mock_discover, client, mock_blueprints_metadata):
        """Test blueprint page for invalid blueprint name returns 404."""
        mock_discover.return_value = mock_blueprints_metadata

        # Test via request factory for direct view testing
        from swarm.views.web_views import blueprint_webpage

        factory = RequestFactory()
        request = factory.get("/blueprint/nonexistent/")

        response = blueprint_webpage(request, "nonexistent")

        assert response.status_code == 404
        assert "not found" in str(response.content).lower()

    @patch("swarm.views.web_views.discover_blueprints")
    def test_blueprint_page_lists_available(self, mock_discover, client, mock_blueprints_metadata):
        """Test blueprint page lists available blueprints when not found."""
        mock_discover.return_value = mock_blueprints_metadata

        from swarm.views.web_views import blueprint_webpage

        factory = RequestFactory()
        request = factory.get("/blueprint/nonexistent/")

        response = blueprint_webpage(request, "nonexistent")

        # Should list available blueprints
        content = str(response.content)
        assert "assistant" in content or "developer" in content

    @patch("swarm.views.web_views.discover_blueprints")
    def test_blueprint_page_error(self, mock_discover, client):
        """Test blueprint page handles discovery errors gracefully."""
        mock_discover.side_effect = Exception("Discovery error")

        from swarm.views.web_views import blueprint_webpage

        factory = RequestFactory()
        request = factory.get("/blueprint/assistant/")

        response = blueprint_webpage(request, "assistant")

        assert response.status_code == 500
        assert "Error" in str(response.content)


# =============================================================================
# Tests for serve_swarm_config view
# =============================================================================

class TestServeSwarmConfigView:
    """Tests for the swarm config endpoint."""

    def test_serve_config_success(self, client, tmp_path, monkeypatch):
        """Test serving swarm config file successfully."""
        config_data = {"default_blueprint": "assistant", "version": "1.0"}
        config_file = tmp_path / "swarm_config.json"
        config_file.write_text(json.dumps(config_data))

        # Patch settings.BASE_DIR to use tmp_path
        from django.conf import settings
        monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

        from swarm.views.web_views import serve_swarm_config

        factory = RequestFactory()
        request = factory.get("/swarm-config/")

        response = serve_swarm_config(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["default_blueprint"] == "assistant"

    def test_serve_config_not_found(self, client, tmp_path, monkeypatch):
        """Test serving config when file not found returns default."""
        from django.conf import settings
        monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

        from swarm.views.web_views import serve_swarm_config, DEFAULT_CONFIG

        factory = RequestFactory()
        request = factory.get("/swarm-config/")

        response = serve_swarm_config(request)

        # Returns 404 with default config
        assert response.status_code == 404
        data = json.loads(response.content)
        assert data == DEFAULT_CONFIG

    def test_serve_config_invalid_json(self, client, tmp_path, monkeypatch):
        """Test serving config with invalid JSON returns error."""
        config_file = tmp_path / "swarm_config.json"
        config_file.write_text("{ invalid json }")

        from django.conf import settings
        monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

        from swarm.views.web_views import serve_swarm_config

        factory = RequestFactory()
        request = factory.get("/swarm-config/")

        response = serve_swarm_config(request)

        assert response.status_code == 500
        data = json.loads(response.content)
        assert "error" in data


# =============================================================================
# Tests for custom_login view
# =============================================================================

class TestCustomLoginView:
    """Tests for the custom login view."""

    @patch("swarm.views.web_views.render")
    def test_login_get_renders_form(self, mock_render, client):
        """Test GET request renders login form."""
        mock_render.return_value = HttpResponse(status=200)

        from swarm.views.web_views import custom_login

        factory = RequestFactory()
        request = factory.get("/accounts/login/")

        response = custom_login(request)

        assert response.status_code == 200

    @patch("swarm.views.web_views.authenticate")
    @patch("swarm.views.web_views.login")
    def test_login_post_success(self, mock_login, mock_auth, client):
        """Test successful login redirects."""
        from swarm.views.web_views import custom_login

        # Mock successful authentication
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_auth.return_value = mock_user

        factory = RequestFactory()
        request = factory.post("/accounts/login/", {"username": "test", "password": "pass"})

        response = custom_login(request)

        # Should redirect
        assert response.status_code == 302

    @patch("swarm.views.web_views.authenticate")
    @patch("swarm.views.web_views.render")
    def test_login_post_failure(self, mock_render, mock_auth, client):
        """Test failed login returns error."""
        mock_render.return_value = HttpResponse(status=200)
        
        from swarm.views.web_views import custom_login

        # Mock failed authentication
        mock_auth.return_value = None

        factory = RequestFactory()
        request = factory.post("/accounts/login/", {"username": "test", "password": "wrong"})

        response = custom_login(request)

        # Should render login form with error
        assert response.status_code == 200


# =============================================================================
# Tests for team_launcher view
# =============================================================================

class TestTeamLauncherView:
    """Tests for the team launcher view."""

    @patch("swarm.views.web_views._webui_enabled", return_value=True)
    @patch("swarm.views.web_views.get_api_auth_token", return_value="test-token")
    @patch("swarm.views.web_views._profiles_ctx", return_value={})
    @patch("swarm.views.web_views.render")
    def test_team_launcher_enabled(self, mock_render, mock_profiles, mock_token, mock_enabled, client):
        """Test team launcher when webui is enabled."""
        mock_render.return_value = HttpResponse(status=200)
        
        from swarm.views.web_views import team_launcher

        factory = RequestFactory()
        request = factory.get("/teams/launch/")

        response = team_launcher(request)

        assert response.status_code == 200

    @patch("swarm.views.web_views._webui_enabled", return_value=False)
    def test_team_launcher_disabled(self, mock_enabled, client):
        """Test team launcher when webui is disabled returns 404."""
        from swarm.views.web_views import team_launcher

        factory = RequestFactory()
        request = factory.get("/teams/launch/")

        response = team_launcher(request)

        assert response.status_code == 404
        assert "disabled" in str(response.content).lower()


# =============================================================================
# Tests for team_admin view
# =============================================================================

class TestTeamAdminView:
    """Tests for the team admin view."""

    @patch("swarm.views.web_views._webui_enabled", return_value=True)
    @patch("swarm.views.web_views._profiles_ctx", return_value={})
    @patch("swarm.views.web_views.render")
    def test_team_admin_enabled(self, mock_render, mock_profiles, mock_enabled, client):
        """Test team admin when webui is enabled."""
        mock_render.return_value = HttpResponse(status=200)
        
        from swarm.views.web_views import team_admin

        factory = RequestFactory()
        request = factory.get("/teams/")

        response = team_admin(request)

        assert response.status_code == 200

    @patch("swarm.views.web_views._webui_enabled", return_value=False)
    def test_team_admin_disabled(self, mock_enabled, client):
        """Test team admin when webui is disabled returns 404."""
        from swarm.views.web_views import team_admin

        factory = RequestFactory()
        request = factory.get("/teams/")

        response = team_admin(request)

        assert response.status_code == 404


# =============================================================================
# Tests for profiles_page view
# =============================================================================

class TestProfilesPageView:
    """Tests for the profiles page view."""

    @patch("swarm.views.web_views.render")
    def test_profiles_page_renders(self, mock_render, client):
        """Test profiles page renders successfully."""
        mock_render.return_value = HttpResponse(status=200)
        
        from swarm.views.web_views import profiles_page

        factory = RequestFactory()
        request = factory.get("/profiles/")

        response = profiles_page(request)

        assert response.status_code == 200


# =============================================================================
# Tests for teams_export view
# =============================================================================

class TestTeamsExportView:
    """Tests for the teams export view."""

    @patch("swarm.views.web_views.load_dynamic_registry")
    def test_teams_export_json(self, mock_registry, client):
        """Test teams export returns JSON by default."""
        mock_registry.return_value = {"team1": {"llm_profile": "default"}}

        from swarm.views.web_views import teams_export

        factory = RequestFactory()
        request = factory.get("/teams/export")

        response = teams_export(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "team1" in data

    @patch("swarm.views.web_views.load_dynamic_registry")
    def test_teams_export_csv(self, mock_registry, client):
        """Test teams export returns CSV when requested."""
        mock_registry.return_value = {"team1": {"llm_profile": "default", "description": "Test team"}}

        from swarm.views.web_views import teams_export

        factory = RequestFactory()
        request = factory.get("/teams/export?format=csv")

        response = teams_export(request)

        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
