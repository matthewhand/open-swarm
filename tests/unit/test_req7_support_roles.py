"""REQ-7: Support/gate/skeptic role looks + Support registration."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SIDEBAR_JS = REPO / "src" / "swarm" / "static" / "js" / "agent_sidebar.js"
SHELL_CSS = REPO / "src" / "swarm" / "static" / "css" / "rest_mode_style.css"
SPA_CSS = REPO / "webui" / "frontend" / "src" / "index.css"
SUPPORT_BP = REPO / "src" / "swarm" / "blueprints" / "support" / "blueprint_support.py"
GATE_BP = REPO / "src" / "swarm" / "blueprints" / "gate" / "blueprint_gate.py"
SKEPTIC_BP = REPO / "src" / "swarm" / "blueprints" / "skeptic" / "blueprint_skeptic.py"


def test_support_is_a_blueprint_with_role():
    text = SUPPORT_BP.read_text(encoding="utf-8")
    assert '"role": "support"' in text
    assert "as_tool" in text
    assert "grok" not in text.lower() or "Do not shell out to grok" in text


def test_gate_and_skeptic_are_role_stubs():
    gate = GATE_BP.read_text(encoding="utf-8")
    skeptic = SKEPTIC_BP.read_text(encoding="utf-8")
    assert '"role": "gate"' in gate
    assert '"role": "skeptic"' in skeptic
    assert "Until wired, all approved" in gate
    assert "findings go back to retry" in skeptic


def test_django_sidebar_styles_roles_not_diamonds():
    js = SIDEBAR_JS.read_text(encoding="utf-8")
    css = SHELL_CSS.read_text(encoding="utf-8")
    assert "data-role" in js
    assert 'os-agent-item--"' in js or "os-agent-item--" in js
    assert 'role === "support"' in js
    assert 'role === "gate"' in js
    assert 'role === "skeptic"' in js
    assert "os-agent-item--support" in css
    assert "os-agent-item--gate" in css
    assert "os-agent-item--skeptic" in css
    assert "os-role-pill--support" in css


def test_spa_role_looks_are_distinct():
    css = SPA_CSS.read_text(encoding="utf-8")
    assert ".os-agent-row--support" in css
    assert ".os-agent-row--gate" in css
    assert ".os-agent-row--skeptic" in css
    assert ".os-code-python" in css
    assert ".os-support-welcome a" in css
