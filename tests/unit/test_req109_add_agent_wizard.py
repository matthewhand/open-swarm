"""REQ-109: + beside favourites opens Add agent popup wizard (CLI | API | Remote).

Intent: Fast path to create a new agent without hunting Settings.
Rules:
1. + control immediately to the right of favourites (dashed / grid) region in left rail.
   Accessible name: 'Add agent'. Tap target >=44px. Works when favourites empty or filled.
2. Overlay: opens popup wizard pane (DaisyUI modal). Chat stays mounted (#364). Esc / backdrop closes.
3. Kind step: chooses CLI | API | Remote. Remote copy says OpenMousBot not OMB (#409).
4. Follow-on steps: create flows per kind (name, blueprint/CLI catalog, remote config).
5. Teams: Out of scope. Agent create only.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
WIZARD_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AddAgentWizard.tsx"
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"


def test_sidebar_has_add_button_beside_favourites():
    content = SIDEBAR_TSX.read_text(encoding="utf-8")
    assert "os-fav-section" in content
    assert "os-fav-add-btn" in content
    assert 'aria-label="Add agent"' in content
    assert 'data-testid="add-agent-button"' in content
    assert "AddAgentWizard" in content
    assert "addWizardOpen" in content


def test_add_agent_wizard_implements_three_kinds_and_openmousbot_copy():
    content = WIZARD_TSX.read_text(encoding="utf-8")
    # Overlay modal
    assert "Modal" in content
    assert "isOpen" in content
    assert "onClose" in content

    # Three kinds present
    assert "'cli'" in content
    assert "'api'" in content
    assert "'remote'" in content
    assert "data-testid=\"kind-option-cli\"" in content
    assert "data-testid=\"kind-option-api\"" in content
    assert "data-testid=\"kind-option-remote\"" in content

    # REQ-409: Remote copy must use OpenMousBot, never OMB in user-facing labels
    assert "OPENMOUSBOT_LABEL" in content
    assert "OpenMousBot" in content

    # Creation API calls
    assert "createCustomBlueprint" in content
    assert "createRemote" in content


def test_css_tap_target_and_flex_layout():
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ".os-fav-section {" in css
    assert ".os-fav-add-btn {" in css
    assert "min-width: 44px;" in css
    assert "min-height: 44px;" in css
