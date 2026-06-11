"""Per-blueprint API smoke tests (SWARM_TEST_MODE).

Guards the regression where non-streaming /v1/chat/completions returned
spinner text ("Generating.") instead of the blueprint's real answer, and
asserts every discoverable blueprint answers over the API surface.
"""

import json

import pytest
from django.test import Client

from swarm.core.blueprint_discovery import discover_blueprints
from swarm.settings import BLUEPRINT_DIRECTORY


def _blueprint_ids() -> list[str]:
    # Discovery imports blueprint modules via file specs, inserting
    # sys.modules entries without proper parent packages — which breaks later
    # real `import swarm.blueprints.<x>.<y>` statements in other test modules.
    # Snapshot and purge whatever discovery adds so collection stays clean.
    import sys

    before = set(sys.modules)
    try:
        ids = sorted(discover_blueprints(str(BLUEPRINT_DIRECTORY)).keys())
    except TypeError:
        ids = sorted(discover_blueprints(directories=[BLUEPRINT_DIRECTORY]).keys())
    for name in set(sys.modules) - before:
        if name.startswith("swarm.blueprints"):
            del sys.modules[name]
    return ids


BLUEPRINTS = _blueprint_ids()

# Blueprints that genuinely cannot answer over the API today, with reasons.
XFAIL: dict[str, str] = {
    "whiskeytango_foxtrot": (
        "run() hangs in SWARM_TEST_MODE (no canned-response path; spawns its "
        "multi-tier agent loop) — tracked in ROADMAP"
    ),
}


@pytest.fixture(autouse=True)
def _test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")


def _post_completion(client: Client, model: str, stream: bool):
    return client.post(
        "/v1/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                **({"stream": True} if stream else {}),
            }
        ),
        content_type="application/json",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("blueprint_id", BLUEPRINTS)
def test_non_streaming_returns_real_answer(client, blueprint_id):
    if blueprint_id in XFAIL:
        pytest.xfail(XFAIL[blueprint_id])
    response = _post_completion(client, blueprint_id, stream=False)
    assert response.status_code == 200, response.content[:300]
    payload = response.json()
    assert payload.get("object") == "chat.completion"
    content = payload["choices"][0]["message"]["content"]
    assert content and content.strip(), "empty completion content"
    assert not content.startswith("Generating"), (
        f"spinner text leaked as the answer: {content[:80]!r}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("blueprint_id", BLUEPRINTS)
def test_streaming_emits_done(client, blueprint_id):
    if blueprint_id in XFAIL:
        pytest.xfail(XFAIL[blueprint_id])
    response = _post_completion(client, blueprint_id, stream=True)
    assert response.status_code == 200, getattr(response, "content", b"")[:300]
    stream = response.streaming_content
    if hasattr(stream, "__aiter__"):  # async streaming response under test client
        import asyncio

        async def _collect():
            return b"".join([chunk async for chunk in stream])

        body = asyncio.run(_collect()).decode()
    else:
        body = b"".join(stream).decode()
    assert "data: [DONE]" in body
    assert '"content"' in body
