from pathlib import Path


def test_req155_settings_dashboard_template_avatar_options():
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "src" / "swarm" / "templates" / "settings_dashboard.html"
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    assert 'id="os-avatar-theme"' in content
    assert '<option value="blobs">Blobs with eyes (default)</option>' in content
    assert '<option value="bland">Bland static circle</option>' in content
    assert '<option value="bee">Bee</option>' in content


def test_req155_chrome_avatar_theme_script_defaults_to_blobs():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "swarm" / "static" / "js" / "chrome_avatar_theme.js"
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")

    assert 'return "blobs";' in content
    assert 'theme === "bland"' in content
    assert 'theme === "bee"' in content
    assert 'localStorage.removeItem(KEY);' in content


def test_req155_frontend_avatar_theme_defaults():
    repo_root = Path(__file__).resolve().parents[2]
    theme_ts_path = repo_root / "webui" / "frontend" / "src" / "lib" / "avatarTheme.ts"
    assert theme_ts_path.exists()
    content = theme_ts_path.read_text(encoding="utf-8")

    assert "defaultAvatarTheme(): AvatarTheme" in content
    assert "return 'blobs'" in content
    assert "'blobs', 'bland', 'default', 'bee'" in content


def test_req155_avatar_theme_picker_labels():
    repo_root = Path(__file__).resolve().parents[2]
    picker_path = repo_root / "webui" / "frontend" / "src" / "components" / "AvatarThemePicker.tsx"
    assert picker_path.exists()
    content = picker_path.read_text(encoding="utf-8")

    assert "Blobs with eyes (default)" in content
    assert "Bland static circle" in content
    assert ">Bee<" in content
    assert "optional choice" in content
