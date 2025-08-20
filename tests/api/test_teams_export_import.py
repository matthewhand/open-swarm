import json

import pytest


@pytest.mark.django_db(transaction=True)
def test_export_json_and_csv_and_import_roundtrip(client, settings):
    settings.ENABLE_WEBUI = True

    # Ensure clean state via reset
    resp = client.post("/teams/", data={"action": "reset"})
    assert resp.status_code in (200, 302)

    # Import JSON
    payload = {"demo1": {"llm_profile": "default", "description": "one"}}
    resp = client.post("/teams/", data={
        "action": "import",
        "import_format": "json",
        "import_data": json.dumps(payload),
        "overwrite": "on",
    })
    assert resp.status_code == 200
    assert b"Imported" in resp.content

    # Export JSON
    resp = client.get("/teams/export?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert "demo1" in data

    # Export CSV
    resp = client.get("/teams/export?format=csv")
    assert resp.status_code == 200
    text = resp.content.decode()
    assert "id,llm_profile,description" in text.splitlines()[0]
    assert any(line.startswith("demo1,") for line in text.splitlines()[1:])

    # Import CSV adds another
    csv_payload = "id,llm_profile,description\nnew-team,default,desc\n"
    resp = client.post("/teams/", data={
        "action": "import",
        "import_format": "csv",
        "import_data": csv_payload,
        "overwrite": "on",
    })
    assert resp.status_code == 200
    assert b"Imported" in resp.content

