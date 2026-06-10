
import pytest
from django.test import RequestFactory
from unittest.mock import patch, MagicMock
from swarm.views.web_views import custom_login

@pytest.mark.django_db
class TestCustomLoginSecurity:
    def test_custom_login_open_redirect_rejected(self):
        factory = RequestFactory()
        # Vulnerable scenario: next parameter points to an external malicious site
        malicious_url = "http://malicious.com"
        request = factory.post(f"/accounts/login/?next={malicious_url}", {"username": "test", "password": "pass"})
        # custom_login in web_views.py uses request.POST, not request.body
        request.POST = {"username": "test", "password": "pass"}

        with patch("swarm.views.web_views.authenticate") as mock_auth, \
             patch("swarm.views.web_views.login") as mock_login:

            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_auth.return_value = mock_user

            response = custom_login(request)

            # It should NOT redirect to malicious_url, but to the default fallback
            assert response.status_code == 302
            assert response.url == "/chatbot/"

    def test_custom_login_safe_redirect_allowed(self):
        factory = RequestFactory()
        safe_url = "/internal-path/"
        request = factory.post(f"/accounts/login/?next={safe_url}", {"username": "test", "password": "pass"})
        request.POST = {"username": "test", "password": "pass"}

        with patch("swarm.views.web_views.authenticate") as mock_auth, \
             patch("swarm.views.web_views.login") as mock_login:

            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_auth.return_value = mock_user

            response = custom_login(request)

            assert response.status_code == 302
            assert response.url == safe_url
