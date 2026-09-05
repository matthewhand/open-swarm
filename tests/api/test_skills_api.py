"""GET /v1/skills/ and GET /v1/skills/<name>/ (REQ-212)."""

import pytest


@pytest.mark.django_db
def test_skills_list_includes_bundled_skill_md_paths(client):
    data = client.get("/v1/skills/").json()
    assert data["object"] == "list"
    names = {row["name"] for row in data["data"]}
    assert "conventional-commit" in names
    row = next(item for item in data["data"] if item["name"] == "conventional-commit")
    assert row["id"] == "conventional-commit"
    assert row["path"].endswith("skills/conventional-commit/SKILL.md")
    assert "instructions" not in row


@pytest.mark.django_db
def test_skill_detail_returns_body_preview(client):
    row = client.get("/v1/skills/conventional-commit/").json()
    assert row["found"] is True
    assert row["name"] == "conventional-commit"
    assert "Conventional Commit" in row["instructions"]
    assert row["path"].endswith("SKILL.md")


@pytest.mark.django_db
def test_skill_detail_missing_fails_honestly(client):
    response = client.get("/v1/skills/nope-not-real/")
    assert response.status_code == 404
    body = response.json()
    assert body["found"] is False
    assert body["name"] == "nope-not-real"
    assert "not found" in body["error"].lower()
    assert "SKILL.md" in body["error"]
