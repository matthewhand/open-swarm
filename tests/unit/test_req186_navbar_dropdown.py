"""REQ-186: Remove mystery navbar You / Default dropdown."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"


def test_navbar_no_mystery_api_or_model_dropdown():
    content = CHAT_PAGE_TSX.read_text(encoding="utf-8")

    # The mystery "You" and "Default" controls were api-model-select and the blueprint picker (availableApiAgents)
    assert 'data-testid="api-model-select"' not in content, "api-model-select must be removed from navbar"
    assert "availableApiAgents" not in content, "availableApiAgents blueprint picker must be removed from navbar"

    # fetchModels and modelsQuery should no longer be in ChatPage
    assert "fetchModels" not in content, "fetchModels should not be imported in ChatPage"
    assert "modelsQuery" not in content, "modelsQuery should not be present in ChatPage"
