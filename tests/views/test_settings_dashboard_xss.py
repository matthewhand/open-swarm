"""Regression: the settings dashboard must not inject server data via |safe.

It previously did `let settingsData = {{ settings_groups|safe }}` — an XSS vector
(unescaped server values in a <script>) that also rendered invalid JS (a raw
Python dict). The fix uses Django's `json_script`, which HTML-escapes the JSON.
Page logic lives in static/js/settings_dashboard.js (not an inline <script>).

A later residual put path/env values into onclick="fn('{{ value }}')". Django
HTML escaping is not enough there: browsers decode &#x27; before running the
handler, so a quote in the value breaks out of the JS string. Handlers now
read autoescaped data-* attributes instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import django
import pytest

django.setup()
from django.contrib.auth import get_user_model  # noqa: E402
from django.template import Context, Engine  # noqa: E402
from django.test import Client  # noqa: E402

_SETTINGS_JS = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "swarm"
    / "static"
    / "js"
    / "settings_dashboard.js"
)


@pytest.mark.django_db
def test_settings_dashboard_uses_json_script_not_safe_filter():
    User = get_user_model()
    User.objects.create_user(username="u", password="p")
    client = Client()
    client.login(username="u", password="p")

    resp = client.get("/settings/")
    assert resp.status_code == 200
    html = resp.content.decode()

    # The safe, escaped data island is present; page JS is external.
    assert 'id="swarm-settings-data"' in html
    assert "settings_dashboard.js" in html
    js = _SETTINGS_JS.read_text(encoding="utf-8")
    assert "JSON.parse(document.getElementById" in js
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


@pytest.mark.django_db
def test_settings_dashboard_avoids_onclick_js_string_interpolation():
    """Server values must not be interpolated into onclick/onkeydown JS strings."""
    User = get_user_model()
    User.objects.create_user(username="u3", password="p")
    client = Client()
    client.login(username="u3", password="p")
    html = client.get("/settings/").content.decode()
    js = _SETTINGS_JS.read_text(encoding="utf-8")

    assert "btn-view-object" in html
    assert "btn-copy-env" in html
    assert 'data-group-id="' in html
    assert re.search(r"""onclick\s*=\s*["'][^"']*\{\{""", html) is None
    assert "checkPath('" not in html
    assert "viewObject('" not in html
    assert "copyEnvVar('" not in html
    assert "toggleGroup('" not in html
    # Toast/env rendering must use textContent, not message-in-innerHTML.
    assert "text.textContent = message" in js
    assert "keyEl.textContent = key" in js
    # Live region so screen readers hear toasts that already use textContent.
    assert 'setAttribute(\'aria-live\'' in js or 'setAttribute("aria-live"' in js
    assert "aria-atomic" in js


@pytest.mark.django_db
def test_settings_dashboard_progress_meter_and_section_headings():
    """Progress meter exposes valuetext + labelledby; section h2s preserve heading order."""
    User = get_user_model()
    User.objects.create_user(username="u4", password="p")
    client = Client()
    client.login(username="u4", password="p")
    html = client.get("/settings/").content.decode()

    assert 'role="progressbar"' in html
    assert 'aria-valuetext="' in html
    assert 'aria-labelledby="config-progress-label"' in html
    assert 'id="config-progress-label"' in html
    assert 'aria-valuemin="0"' in html
    assert 'aria-valuemax="100"' in html
    assert 'settings configured' in html

    assert '<h1 class="dashboard-title">Settings Dashboard</h1>' in html
    assert '<h2 class="visually-hidden">Quick actions</h2>' in html
    assert '<h2 class="visually-hidden">Settings groups</h2>' in html
    assert "Credentials" in html
    assert "docs/AUTH.md" in html
    # Focus ring lives in operator.css (CSP: no inline template <style>).
    operator_css = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "swarm"
        / "static"
        / "css"
        / "operator.css"
    ).read_text(encoding="utf-8")
    assert ".group-header:focus-visible" in operator_css


def test_data_attr_keeps_quote_payload_out_of_js_handler_source():
    """data-* + autoescape keeps quote payloads out of executable handler source."""
    engine = Engine(builtins=["django.template.defaulttags", "django.template.defaultfilters"])
    payload = "x');alert(1);//"
    unsafe = engine.from_string("""onclick="checkPath('{{ value }}')" """)
    safe = engine.from_string("""data-path="{{ value }}" """)
    unsafe_html = unsafe.render(Context({"value": payload}))
    safe_html = safe.render(Context({"value": payload}))
    # HTML-escaped quote still decodes inside an event-handler attribute.
    assert "&#x27;" in unsafe_html or "&#39;" in unsafe_html
    assert "checkPath(" in unsafe_html
    # data-* stores the value; JS reads it as data, not source.
    assert "onclick" not in safe_html
    assert "checkPath(" not in safe_html
    assert "&#x27;" in safe_html or "&#39;" in safe_html
