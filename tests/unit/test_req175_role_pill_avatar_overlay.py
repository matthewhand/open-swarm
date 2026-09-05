"""REQ-175: Role badges/pills overlay the rail avatar (not beside name or on second row)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SIDEBAR_TSX = REPO_ROOT / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"


def test_sidebar_role_badge_overlays_avatar():
    content = SIDEBAR_TSX.read_text(encoding="utf-8")

    # Verify role badge has avatar overlay indicator / styling
    assert 'data-avatar-overlay="true"' in content
    assert "roleBadgeNode" in content

    # REQ-67 contract preserved: className exact template literal
    assert re.search(
        r"className=\{`os-agent-role-badge \$\{roleCssClass\(role\)\}`\}",
        content,
    )

    # Avatar slot (relative) wraps mark + role badge so the pill overlays the avatar
    assert re.search(
        r'<span className="os-agent-row__avatar-slot relative inline-flex shrink-0 items-center justify-center">\s*\{mark\}\s*\{roleBadgeNode\}\s*</span>',
        content,
    )
    assert "position: 'absolute'" in content


def test_second_row_does_not_contain_role_badge_chip():
    content = SIDEBAR_TSX.read_text(encoding="utf-8")

    # In single agent row, second row has snippet and optional taskCount, but NOT badge ? <span ...>
    agent_second_row = re.search(
        r'\{snippet \|\| agent\.description\}\s*</span>\s*\{taskCount > 1',
        content,
    )
    assert agent_second_row is not None, "Second row should not reserve role badge chip beside snippet"

    # In team row, second row only has team snippet
    team_second_row = re.search(
        r'\{teamSnippet \|\| team\.description\}\s*</span>\s*</span>\s*</span>\s*</Link>',
        content,
    )
    assert team_second_row is not None, "Team second row should not contain Team badge"

    # In remote row, second row only has remote snippet
    remote_second_row = re.search(
        r'\{remoteSnippet \|\| \(remote as any\)\.description \|\| \'Remote team\'\}\s*</span>\s*</span>\s*</span>\s*</Link>',
        content,
    )
    assert remote_second_row is not None, "Remote second row should not contain Remote badge"
