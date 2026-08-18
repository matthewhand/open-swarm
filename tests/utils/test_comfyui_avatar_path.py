"""Path traversal guards for ComfyUI avatar storage."""

from pathlib import Path

import pytest
from django.conf import settings

from swarm.utils import comfyui_client
from swarm.utils.comfyui_client import (
    ComfyUIClient,
    _safe_avatar_blueprint_slug,
    _safe_comfyui_output_filename,
)


class TestSafeAvatarBlueprintSlug:
    def test_normal_name_spaces_to_underscores(self):
        assert _safe_avatar_blueprint_slug("My Agent") == "my_agent"

    def test_strips_traversal_and_separators(self):
        evil = "../../../outside/pwned_agent"
        slug = _safe_avatar_blueprint_slug(evil)
        assert ".." not in slug
        assert "/" not in slug
        assert "\\" not in slug
        assert slug == "outside_pwned_agent"

    def test_empty_falls_back(self):
        assert _safe_avatar_blueprint_slug("   ") == "agent"
        assert _safe_avatar_blueprint_slug("!!!") == "agent"


class TestSafeComfyuiOutputFilename:
    def test_accepts_plain_basename(self):
        assert _safe_comfyui_output_filename("ComfyUI_00001_.png") == "ComfyUI_00001_.png"

    @pytest.mark.parametrize(
        "evil",
        [
            "../evil.png",
            "../../etc/passwd",
            "/tmp/evil.png",
            "subdir/image.png",
            "..",
            ".",
            "",
            "C:\\Windows\\evil.png",
            "\\absolute\\evil.png",
        ],
    )
    def test_rejects_traversal_and_absolute(self, evil):
        assert _safe_comfyui_output_filename(evil) is None


class TestSaveAvatarImageTraversal:
    def test_blueprint_traversal_stays_under_avatar_root(self, tmp_path, monkeypatch):
        """Evil blueprint_name must not write outside AVATAR_STORAGE_PATH."""
        avatar_root = tmp_path / "avatars"
        avatar_root.mkdir()
        escape_target = tmp_path / "outside"
        escape_target.mkdir()
        comfy_out = tmp_path / "comfy_out"
        comfy_out.mkdir()
        source = comfy_out / "gen.png"
        source.write_bytes(b"png-bytes")

        monkeypatch.setattr(settings, "AVATAR_STORAGE_PATH", avatar_root)
        monkeypatch.setattr(comfyui_client, "COMFYUI_OUTPUT_DIR", comfy_out)

        client = ComfyUIClient()
        evil_name = "../../../outside/pwned"
        result = client._save_avatar_image("gen.png", evil_name)

        assert result is not None
        assert ".." not in result
        assert "/outside/" not in result
        slug = _safe_avatar_blueprint_slug(evil_name)
        expected = avatar_root / f"{slug}_avatar.png"
        assert expected.resolve().is_file()
        assert expected.resolve().parent == avatar_root.resolve()
        assert not (escape_target / "pwned_avatar.png").exists()
        assert list(escape_target.iterdir()) == []

    def test_rejects_comfyui_filename_traversal(self, tmp_path, monkeypatch):
        avatar_root = tmp_path / "avatars"
        avatar_root.mkdir()
        comfy_out = tmp_path / "comfy_out"
        comfy_out.mkdir()
        # File exists outside comfy output — must not be readable via traversal name.
        outside = tmp_path / "secret.png"
        outside.write_bytes(b"secret")

        monkeypatch.setattr(settings, "AVATAR_STORAGE_PATH", avatar_root)
        monkeypatch.setattr(comfyui_client, "COMFYUI_OUTPUT_DIR", comfy_out)

        client = ComfyUIClient()
        result = client._save_avatar_image("../secret.png", "safe_agent")
        assert result is None
        assert list(avatar_root.iterdir()) == []

    def test_rejects_absolute_comfyui_filename(self, tmp_path, monkeypatch):
        avatar_root = tmp_path / "avatars"
        avatar_root.mkdir()
        comfy_out = tmp_path / "comfy_out"
        comfy_out.mkdir()
        absolute_src = tmp_path / "absolute.png"
        absolute_src.write_bytes(b"abs")

        monkeypatch.setattr(settings, "AVATAR_STORAGE_PATH", avatar_root)
        monkeypatch.setattr(comfyui_client, "COMFYUI_OUTPUT_DIR", comfy_out)

        client = ComfyUIClient()
        result = client._save_avatar_image(str(absolute_src), "safe_agent")
        assert result is None
        assert list(avatar_root.iterdir()) == []

    def test_happy_path_copies_under_root(self, tmp_path, monkeypatch):
        avatar_root = tmp_path / "avatars"
        avatar_root.mkdir()
        comfy_out = tmp_path / "comfy_out"
        comfy_out.mkdir()
        source = comfy_out / "ComfyUI_00001_.png"
        source.write_bytes(b"png-bytes")

        monkeypatch.setattr(settings, "AVATAR_STORAGE_PATH", avatar_root)
        monkeypatch.setattr(settings, "AVATAR_URL_PREFIX", "/avatars/")
        monkeypatch.setattr(comfyui_client, "COMFYUI_OUTPUT_DIR", comfy_out)

        client = ComfyUIClient()
        result = client._save_avatar_image("ComfyUI_00001_.png", "My Agent")
        assert result == "/avatars/my_agent_avatar.png"
        dest = avatar_root / "my_agent_avatar.png"
        assert dest.read_bytes() == b"png-bytes"
        assert dest.resolve().parent == avatar_root.resolve()
