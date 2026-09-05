"""REQ-186 / #744: Remove mystery navbar You / Default dropdown."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_PAGE_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"


def test_navbar_no_mystery_api_or_model_dropdown():
    content = CHAT_PAGE_TSX.read_text(encoding="utf-8")

    # #679 removed api-model-select + availableApiAgents but left api-select on
    # api_agent (LLM profile ids / "default"). That leftover is the regression.
    assert 'data-testid="api-select"' not in content, "api-select must stay out of the navbar"
    assert 'data-testid="api-model-select"' not in content, "api-model-select must be removed from navbar"
    assert "availableApiAgents" not in content, "availableApiAgents blueprint picker must be removed from navbar"
    assert "availableApiModels" not in content, "navbar must not list LLM profiles as a model dropdown"
    assert "currentApiModel" not in content, "navbar must not keep an API model select value"

    # fetchModels and modelsQuery should no longer be in ChatPage
    assert "fetchModels" not in content, "fetchModels should not be imported in ChatPage"
    assert "fetchLlmProfiles" not in content, "LLM profiles belong in Settings / Agent Editor, not ChatPage navbar"
    assert "modelsQuery" not in content, "modelsQuery should not be present in ChatPage"

    # Do not resurrect a cryptic dual-dropdown (#676 cascading picker is a later REQ).
    assert 'aria-label="API"' not in content, "navbar must not expose an unlabeled API identity/profile select"
