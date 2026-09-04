from pathlib import Path


def test_req118_agent_sidebar_server_icon_and_popup():
    repo_root = Path(__file__).resolve().parents[2]
    sidebar_path = repo_root / "webui" / "frontend" / "src" / "components" / "AgentSidebar.tsx"
    assert sidebar_path.exists()
    content = sidebar_path.read_text(encoding="utf-8")

    assert "data-testid=\"rail-server-icon\"" in content
    assert "RemoteSessionsPopup" in content
    assert "os-rail-hostname-row" in content
    assert "Server className=" in content


def test_req118_remote_sessions_popup_component():
    repo_root = Path(__file__).resolve().parents[2]
    popup_path = repo_root / "webui" / "frontend" / "src" / "components" / "RemoteSessionsPopup.tsx"
    assert popup_path.exists()
    content = popup_path.read_text(encoding="utf-8")

    assert "cleanRemoteUrl" in content
    assert "isBrowsableRemote" in content
    assert "target=\"_blank\"" in content
    assert "rel=\"noopener noreferrer\"" in content
    assert "No remotes configured" in content
    assert "remoteDisplayName" in content
