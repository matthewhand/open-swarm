"""API tests for /v1/speech/ (REQ-77). Stub HTTP only — no live paid calls."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from swarm.core import speech as speech_core


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate_speech(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "swarm_config.json"
    cfg.write_text(json.dumps({"llm": {}}), encoding="utf-8")
    monkeypatch.setenv("SWARM_CONFIG_PATH", str(cfg))
    for name in (
        "SPEECH_STT_BASE_URL",
        "SPEECH_TTS_BASE_URL",
        "SPEECH_STT_SOURCE",
        "SPEECH_TTS_SOURCE",
        "STT_API_KEY",
        "TTS_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    yield cfg


def test_get_defaults_are_system_and_have_no_secrets(api_client):
    resp = api_client.get("/v1/speech/?probe=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "speech"
    assert body["stt"]["source"] == "system"
    assert body["tts"]["source"] == "system"
    assert body["stt"]["base_url"] == ""
    assert body["stt"]["status"] == "system"
    dumped = json.dumps(body)
    assert "sk-" not in dumped
    assert "api_key" not in body["stt"]
    assert ":8001" not in dumped


def test_patch_persists_env_name_only(api_client, _isolate_speech: Path):
    live = api_client.patch(
        "/v1/speech/",
        {"stt": {"base_url": "http://127.0.0.1:9", "api_key": "sk-live-secret"}},
        format="json",
    )
    assert live.status_code == 400
    assert "api_key_env" in live.json()["error"]

    resp = api_client.patch(
        "/v1/speech/",
        {
            "stt": {
                "source": "custom",
                "base_url": "http://127.0.0.1:9",
                "model": "whisper-1",
                "api_key_env": "STT_API_KEY",
            },
            "tts": {
                "source": "system",
                "base_url": "",
                "model": "",
                "api_key_env": "TTS_API_KEY",
            },
        },
        format="json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stt"]["base_url"] == "http://127.0.0.1:9"
    assert body["stt"]["source"] == "custom"
    assert body["stt"]["api_key_env"] == "STT_API_KEY"
    assert body["tts"]["source"] == "system"
    assert "sk-" not in json.dumps(body)
    data = json.loads(_isolate_speech.read_text(encoding="utf-8"))
    assert data["speech"]["stt"]["api_key"] == "${STT_API_KEY}"
    assert data["speech"]["stt"]["api_key_env"] == "STT_API_KEY"


def test_patch_refuses_port_8001(api_client):
    resp = api_client.patch(
        "/v1/speech/",
        {"stt": {"source": "custom", "base_url": "http://127.0.0.1:8001"}},
        format="json",
    )
    assert resp.status_code == 400
    assert ":8001" in resp.json()["error"]


def test_transcribe_disabled_when_unset(api_client):
    resp = api_client.post(
        "/v1/speech/transcribe/",
        {"file": SimpleUploadedFile("clip.webm", b"abc", content_type="audio/webm")},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "not configured" in resp.json()["error"]


def test_transcribe_and_speak_use_stubs(api_client, _isolate_speech: Path):
    speech_core.persist_settings(
        stt={"source": "custom", "base_url": "http://127.0.0.1:9", "model": "stub"},
        tts={"source": "custom", "base_url": "http://127.0.0.1:9", "model": "stub"},
        config_path=_isolate_speech,
    )

    with patch("swarm.core.speech.transcribe_audio", return_value="hello stub"):
        resp = api_client.post(
            "/v1/speech/transcribe/",
            {"file": SimpleUploadedFile("clip.webm", b"webm-bytes", content_type="audio/webm")},
            format="multipart",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "transcription"
    assert body["text"] == "hello stub"
    assert body["path"] == "custom"
    assert "sk-" not in json.dumps(body)

    with patch(
        "swarm.core.speech.synthesize_speech",
        return_value=(b"ID3stub", "audio/mpeg"),
    ):
        spoken = api_client.post("/v1/speech/speak/", {"text": "Read this"}, format="json")
    assert spoken.status_code == 200
    assert spoken["Content-Type"].startswith("audio/")
    assert spoken.content == b"ID3stub"
    assert spoken["X-Speech-Path"] == "custom"
