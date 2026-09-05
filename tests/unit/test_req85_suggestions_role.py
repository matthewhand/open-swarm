"""REQ-85 chrome + codegen contracts for the suggestions role."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPA_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
DJANGO_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
TEAM_JS = REPO / "src" / "swarm" / "static" / "js" / "team_creator.js"
CODEGEN = REPO / "src" / "swarm" / "views" / "agent_creator_views.py"
CHIPS = REPO / "webui" / "frontend" / "src" / "components" / "SuggestionChips.tsx"
CHAT = REPO / "webui" / "frontend" / "src" / "pages" / "ChatPage.tsx"


def test_badge_only_suggestions_chrome():
    spa = SPA_CSS.read_text(encoding="utf-8")
    django = DJANGO_CSS.read_text(encoding="utf-8")
    assert '.os-agent-role-badge[data-role="suggestions"]' in spa
    assert '.os-agent-role-badge[data-role="suggestions"]' in django
    assert ".os-agent-row--suggestions" not in spa
    assert ".os-agent-row--suggestions" not in django
    assert ".os-suggestion-chips" in spa
    assert ".os-suggestion-chip" in spa


def test_editor_and_team_can_assign_suggestions():
    team = TEAM_JS.read_text(encoding="utf-8")
    assert 'value="suggestions"' in team
    editor = (REPO / "webui" / "frontend" / "src" / "components" / "AgentEditor.tsx").read_text(
        encoding="utf-8"
    )
    assert "suggestions" in editor
    assert "Use suggestions" in editor or "USE_SUGGESTIONS_LABEL" in editor


def test_codegen_wires_suggestions_as_tool():
    src = CODEGEN.read_text(encoding="utf-8")
    assert "attach_suggestions_as_tool" in src
    assert 'find_role_agent(self._agents, "suggestions")' in src


def test_chips_are_controls_not_bubbles():
    tsx = CHIPS.read_text(encoding="utf-8")
    assert "btn" in tsx
    assert "suggestion-chips" in tsx
    chat = CHAT.read_text(encoding="utf-8")
    assert "SuggestionChips" in chat
    assert "chooseSuggestion" in chat
