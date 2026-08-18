"""UX fleet: bare SPA dual-paths redirect to canonical Django operator UI.

These exercise the *shipped* urlpatterns (RedirectView entries in swarm.urls)
via the Django test client — not a reimplementation of the map.
"""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.fixture
def webui_on(settings, monkeypatch):
    """Ensure Web UI views are not gated off (env + settings)."""
    monkeypatch.setenv("ENABLE_WEBUI", "true")
    settings.ENABLE_WEBUI = True
    return settings


@pytest.mark.django_db
class TestSpaToDjangoCanonicalRedirects:
    """Bare paths that used to dual-mount the React shell must 302 to Django."""

    @pytest.mark.parametrize(
        "path,expected_location",
        [
            ("/teams", "/teams/launch/"),
            ("/blueprints", "/blueprint-library/"),
            ("/settings", "/settings/"),
            ("/agent-creator", "/agent-creator/"),
        ],
    )
    def test_bare_spa_path_redirects_to_django(self, client, path, expected_location):
        response = client.get(path)
        assert response.status_code == 302, (
            f"{path} should redirect to canonical Django UI, got {response.status_code}"
        )
        assert response.url == expected_location

    def test_query_string_preserved_on_teams_redirect(self, client):
        response = client.get("/teams?blueprint=hybrid_team")
        assert response.status_code == 302
        assert response.url.startswith("/teams/launch/")
        assert "blueprint=hybrid_team" in response.url

    def test_named_redirect_routes_exist(self):
        assert reverse("spa_teams_to_django") == "/teams"
        assert reverse("spa_blueprints_to_django") == "/blueprints"
        assert reverse("spa_settings_to_django") == "/settings"
        assert reverse("spa_agent_creator_to_django") == "/agent-creator"

    def test_trailing_slash_django_routes_not_redirect_loops(self, client, webui_on):
        """Canonical Django routes keep working (no redirect-to-self loops)."""
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxcanon", password="ux-canon-pass")
        client.force_login(user)
        for path in ("/teams/", "/teams/launch/", "/settings/", "/blueprint-library/"):
            response = client.get(path)
            assert response.status_code in (200, 302, 301), (
                f"{path} unexpected status {response.status_code}: "
                f"{response.content[:120]!r}"
            )
            if response.status_code in (301, 302):
                assert response.url != path


@pytest.mark.django_db
class TestUxShellTemplateContracts:
    """Structural contracts for shell IA / density shipped in templates."""

    def test_base_shell_has_five_primary_destinations_and_more(self, client):
        # base.html is extended by many pages; settings requires login often.
        # Use login page which extends base, or force_login.
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxshell", password="ux-shell-pass")
        client.force_login(user)
        response = client.get("/settings/")
        assert response.status_code == 200
        html = response.content.decode()
        for label in ("Home", "Blueprints", "Teams", "Sessions", "Settings"):
            assert label in html
        assert "More" in html
        assert "os-bottom-nav" in html
        assert "Skip to main content" in html
        assert 'id="os-main"' in html
        # GitHub not a bare primary peer string next to Settings as sole link —
        # demoted under More dropdown.
        assert 'id="moreNavDropdown"' in html

    def test_profiles_marks_profiles_item_active_not_teams(self, client):
        import re

        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxprof", password="ux-prof-pass")
        client.force_login(user)
        response = client.get("/profiles/")
        assert response.status_code == 200
        html = response.content.decode()
        # LLM profiles dropdown item is current page
        profiles_item = re.search(
            r'<a class="dropdown-item active"[^>]*href="/profiles/"[^>]*aria-current="page"',
            html,
        )
        assert profiles_item, "expected active Profiles dropdown item with aria-current"
        # Teams primary toggle must not be active for /profiles/
        teams_toggle = re.search(
            r'<a class="nav-link dropdown-toggle([^"]*)"[^>]*id="teamsNavDropdown"',
            html,
        )
        assert teams_toggle, "expected Teams dropdown toggle"
        assert "active" not in teams_toggle.group(1)
        # Mobile bottom: Teams is-active only for /teams/, not /profiles/
        teams_bottom = re.search(
            r'<a class="os-bottom-nav__item([^"]*)"[^>]*>\s*'
            r'<span class="os-bottom-nav__label">Teams</span>',
            html,
        )
        assert teams_bottom, "expected Teams bottom-nav item"
        assert "is-active" not in teams_bottom.group(1)

    def test_sessions_marks_sessions_nav_active(self, client):
        import re

        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxsessnav", password="ux-sess-nav")
        client.force_login(user)
        response = client.get("/sessions/")
        assert response.status_code == 200
        html = response.content.decode()
        sessions_link = re.search(
            r'<a class="nav-link active"[^>]*href="/sessions/"[^>]*aria-current="page"',
            html,
        )
        assert sessions_link, "expected active Sessions nav link"
        teams_toggle = re.search(
            r'<a class="nav-link dropdown-toggle([^"]*)"[^>]*id="teamsNavDropdown"',
            html,
        )
        assert teams_toggle and "active" not in teams_toggle.group(1)

    def test_blueprint_library_ships_client_pagination(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxlib", password="ux-lib-pass")
        client.force_login(user)
        response = client.get("/blueprint-library/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "BP_PAGE_SIZE" in html
        assert "Show more" in html
        assert "bpShowMore" in html

    def test_session_explorer_ships_scroll_containment(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxsess", password="ux-sess-pass")
        client.force_login(user)
        response = client.get("/sessions/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "se-list-scroll" in html

    def test_agent_creator_progressive_disclosure(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxac", password="ux-ac-pass")
        client.force_login(user)
        response = client.get("/agent-creator/")
        assert response.status_code == 200
        html = response.content.decode()
        # Persona / Tags optional panels collapsed by default
        assert 'data-bs-target="#acc-persona"' in html
        assert "accordion-button collapsed" in html
        assert 'id="acc-persona" class="accordion-collapse collapse"' in html
        assert 'id="acc-behavior" class="accordion-collapse collapse"' in html
        # Essentials open
        assert 'id="acc-identity" class="accordion-collapse collapse show"' in html

    def test_agent_creator_uses_data_action_not_onclick(self, client):
        """Static creator actions bind via data-action delegation (no inline onclick)."""
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxac2", password="ux-ac-pass")
        client.force_login(user)
        response = client.get("/agent-creator/")
        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-action="generate-agent"' in html
        assert 'data-action="clear-form"' in html
        assert 'data-action="validate-code"' in html
        assert 'data-action="save-agent"' in html
        assert "onclick=" not in html
        assert "AGENT_CREATOR_ACTIONS" in html

    def test_team_creator_uses_data_action_not_onclick(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxteam", password="ux-team-pass")
        client.force_login(user)
        response = client.get("/team-creator/")
        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-action="add-member"' in html
        assert 'data-action="generate-team"' in html
        assert 'data-action="clear-team"' in html
        assert 'data-action="validate-team"' in html
        assert 'data-action="save-team"' in html
        assert 'data-action="remove-member"' in html
        assert "onclick=" not in html
        assert "TEAM_CREATOR_ACTIONS" in html

    def test_agent_creator_pro_redirects_to_canonical(self, client):
        """Unwired Pro UI soft-redirects to /agent-creator/ (preserve query)."""
        response = client.get("/agent-creator-pro/?from=nav")
        assert response.status_code in (301, 302)
        assert response["Location"].endswith("/agent-creator/?from=nav") or \
            response["Location"] == "/agent-creator/?from=nav"

    def test_my_blueprints_runner_posts_chat_completions(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxmb", password="ux-mb-pass")
        client.force_login(user)
        response = client.get("/blueprint-library/my-blueprints/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "Simulate run (demo)" not in html
        assert "Client-side demo only" not in html
        assert "/v1/chat/completions" in html
        assert "Run via API" in html
        assert "/chat?blueprint=" in html
        assert "/teams/launch/" in html

    def test_settings_unwired_actions_are_disabled(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxset", password="ux-set-pass")
        client.force_login(user)
        response = client.get("/settings/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "Validate Config (not available)" in html
        assert "Export (not available)" in html
        assert "(soon)" not in html
        assert "btn-check-path" not in html
        assert "onclick=\"validateConfiguration()\"" not in html
        assert "onclick=\"exportEnvVars()\"" not in html
        assert "onclick=\"checkPath(" not in html

    def test_team_creator_validate_marked_unavailable(self, client):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="uxtd", password="ux-td-pass")
        client.force_login(user)
        response = client.get("/team-creator/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "Validate (not available)" in html
        assert "Validate (demo)" not in html
        assert "Preview Draft" in html
        assert "no server-side team validation" in html
