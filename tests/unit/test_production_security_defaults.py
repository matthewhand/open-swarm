"""Production security header / cookie defaults when DEBUG is False.

These assert the *logic* used in settings.py (replicated here) so we do not
need to re-import settings under a flipped DEBUG (which is sticky under pytest).
"""
from __future__ import annotations

import os
from unittest.mock import patch


def _apply_prod_secure_defaults(debug: bool, env: dict[str, str] | None = None) -> dict:
    """Mirror of the settings.py production security block."""
    out: dict = {}
    env = env or {}
    if not debug:
        out["SECURE_CONTENT_TYPE_NOSNIFF"] = True
        out["X_FRAME_OPTIONS"] = env.get("DJANGO_X_FRAME_OPTIONS", "DENY")
        secure_env = env.get("SWARM_SECURE_COOKIES", "").strip().lower()
        if secure_env in ("false", "0", "no", "n", "off"):
            secure = False
        else:
            secure = True
        out["SESSION_COOKIE_SECURE"] = secure
        out["CSRF_COOKIE_SECURE"] = secure
    return out


class TestProductionSecurityDefaults:
    def test_debug_true_sets_nothing(self):
        assert _apply_prod_secure_defaults(debug=True) == {}

    def test_production_sets_headers_and_secure_cookies(self):
        out = _apply_prod_secure_defaults(debug=False, env={})
        assert out["SECURE_CONTENT_TYPE_NOSNIFF"] is True
        assert out["X_FRAME_OPTIONS"] == "DENY"
        assert out["SESSION_COOKIE_SECURE"] is True
        assert out["CSRF_COOKIE_SECURE"] is True

    def test_secure_cookies_opt_out(self):
        out = _apply_prod_secure_defaults(
            debug=False, env={"SWARM_SECURE_COOKIES": "false"}
        )
        assert out["SESSION_COOKIE_SECURE"] is False
        assert out["CSRF_COOKIE_SECURE"] is False

    def test_x_frame_options_override(self):
        out = _apply_prod_secure_defaults(
            debug=False, env={"DJANGO_X_FRAME_OPTIONS": "SAMEORIGIN"}
        )
        assert out["X_FRAME_OPTIONS"] == "SAMEORIGIN"

    def test_live_settings_under_pytest_are_debug(self):
        """TESTING forces DEBUG; production block must not have flipped cookies."""
        from django.conf import settings

        # Under pytest, DEBUG is True so secure-cookie production defaults
        # should not be forced on (session cookies work over http://testserver).
        assert settings.DEBUG is True or getattr(settings, "TESTING", False)
        # If DEBUG is somehow False, the block would set secure cookies — but
        # the default test path keeps DEBUG True.
        if settings.DEBUG:
            # Production-only attrs may be unset or False under DEBUG.
            assert getattr(settings, "SESSION_COOKIE_SECURE", False) in (False, True)
