"""REQ-79 — built SPA is served with a hydratable #root (not empty / not Django cards)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def spa_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><body>"
        '<div id="root"></div>'
        '<script type="module" src="/assets/index.js"></script>'
        "</body></html>",
        encoding="utf-8",
    )
    return dist


def test_index_serves_spa_root_when_dist_present(client, spa_dist):
    with patch("swarm.views.web_views._ensure_frontend_built", return_value=spa_dist):
        response = client.get("/")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="root"' in body
    assert "Launch Team" not in body
    assert "os-action-card" not in body


def test_chat_serves_spa_root_when_dist_present(client, spa_dist):
    with patch("swarm.views.web_views._get_frontend_path", return_value=spa_dist):
        response = client.get("/chat")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="root"' in body
    assert "<script" in body


def test_chat_404_without_dist_is_honest(client):
    with patch("swarm.views.web_views._get_frontend_path", return_value=None):
        response = client.get("/chat")
    assert response.status_code == 404
