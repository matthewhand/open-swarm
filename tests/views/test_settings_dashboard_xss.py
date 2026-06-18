"""Regression: the settings dashboard must not inject server data via |safe.

It previously did `let settingsData = {{ settings_groups|safe }}` — an XSS vector
(unescaped server values in a <script>) that also rendered invalid JS (a raw
Python dict). The fix uses Django's `json_script`, which HTML-escapes the JSON.
"""

from __future__ import annotations

import django
import pytest

django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402


@pytest.mark.django_db
def test_settings_dashboard_uses_json_script_not_safe_filter():
    User = get_user_model()
    User.objects.create_user(username="u", password="p")
    client = Client()
    client.login(username="u", password="p")

    resp = client.get("/settings/")
    assert resp.status_code == 200
    html = resp.content.decode()

    # The safe, escaped data island is present and consumed via JSON.parse.
    assert 'id="swarm-settings-data"' in html
    assert "JSON.parse(document.getElementById" in html
    # The old unescaped injection is gone.
    assert "settings_groups|safe" not in html
    assert "let settingsData = {" not in html


@pytest.mark.django_db
def test_settings_dashboard_escapes_script_in_json_island():
    # json_script must escape angle brackets so a value can't break out of the
    # <script type="application/json"> container.
    User = get_user_model()
    User.objects.create_user(username="u2", password="p")
    client = Client()
    client.login(username="u2", password="p")
    html = client.get("/settings/").content.decode()
    # Find the data island; it must not contain a raw closing script tag.
    start = html.find('id="swarm-settings-data"')
    assert start != -1
    island = html[start : html.find("</script>", start)]
    assert "</script" not in island.replace("\\u003c", "")  # only escaped form allowed
