"""REQ-45 runtime-mode banner: honest modes, never fake green."""
from pathlib import Path

from swarm.core.runtime_mode import (
    ENV_RUNTIME_MODE,
    ENV_RUNTIME_MODE_ALIAS,
    MODE_BARE_METAL,
    MODE_SANDBOX_HOME,
    MODE_SANDBOX_ISOLATED,
    MODE_UNKNOWN,
    TONE_INFO,
    TONE_UNKNOWN,
    TONE_WARNING,
    normalize_runtime_mode,
    read_runtime_mode,
    runtime_banner,
)

REPO = Path(__file__).resolve().parents[2]


def test_known_modes_and_aliases():
    assert normalize_runtime_mode("bare-metal") == MODE_BARE_METAL
    assert normalize_runtime_mode("bare_metal") == MODE_BARE_METAL
    assert normalize_runtime_mode("SANDBOX-HOME") == MODE_SANDBOX_HOME
    assert normalize_runtime_mode("sandbox_isolated") == MODE_SANDBOX_ISOLATED


def test_missing_and_blank_are_unknown():
    assert normalize_runtime_mode(None) == MODE_UNKNOWN
    assert normalize_runtime_mode("") == MODE_UNKNOWN
    assert normalize_runtime_mode("   ") == MODE_UNKNOWN


def test_unrecognized_and_pathlike_are_unknown_never_green():
    for raw in ("docker", "/home/ubuntu", "C:\\Users\\matt", "$HOME", "sandbox-home /opt"):
        banner = runtime_banner(raw)
        assert banner["mode"] == MODE_UNKNOWN
        assert banner["known"] is False
        assert banner["tone"] == TONE_UNKNOWN
        assert banner["tone"] != TONE_INFO


def test_bare_metal_and_sandbox_home_are_warnings():
    metal = runtime_banner(MODE_BARE_METAL)
    home = runtime_banner(MODE_SANDBOX_HOME)
    assert metal["tone"] == TONE_WARNING
    assert home["tone"] == TONE_WARNING
    assert "bare metal" in metal["title"].lower() or "bare metal" in metal["message"].lower()
    assert "$HOME" in home["message"]
    assert "SWARM_SANDBOX_ROOT" in home["message"]


def test_sandbox_isolated_is_info_not_unknown():
    isolated = runtime_banner(MODE_SANDBOX_ISOLATED)
    assert isolated["known"] is True
    assert isolated["tone"] == TONE_INFO
    assert isolated["tone"] != TONE_UNKNOWN
    assert "$HOME" in isolated["message"]


def test_banner_copy_has_no_real_host_paths_or_secrets():
    for mode in (MODE_BARE_METAL, MODE_SANDBOX_HOME, MODE_SANDBOX_ISOLATED, MODE_UNKNOWN):
        payload = runtime_banner(mode)
        blob = " ".join(str(v) for v in payload.values())
        assert "/home/" not in blob
        assert "C:\\" not in blob
        assert "api_key" not in blob.lower()
        assert "token" not in blob.lower()
        assert payload.get("env_var") == ENV_RUNTIME_MODE


def test_read_runtime_mode_from_environ():
    assert read_runtime_mode({}) == MODE_UNKNOWN
    assert read_runtime_mode({ENV_RUNTIME_MODE: "sandbox-isolated"}) == MODE_SANDBOX_ISOLATED
    assert read_runtime_mode({ENV_RUNTIME_MODE: "/tmp/not-a-mode"}) == MODE_UNKNOWN
    # Pinokio / base compose use SWARM_RUNTIME; accept it when the canonical name is unset.
    assert read_runtime_mode({ENV_RUNTIME_MODE_ALIAS: "sandbox-home"}) == MODE_SANDBOX_HOME
    assert read_runtime_mode({
        ENV_RUNTIME_MODE: "sandbox-isolated",
        ENV_RUNTIME_MODE_ALIAS: "sandbox-home",
    }) == MODE_SANDBOX_ISOLATED


def test_compose_wires_runtime_mode():
    base = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    dev = (REPO / "docker-compose.dev.yml").read_text(encoding="utf-8")
    assert 'SWARM_RUNTIME: "${SWARM_RUNTIME:-sandbox-home}"' in base
    assert 'SWARM_RUNTIME_MODE: "${SWARM_RUNTIME_MODE:-sandbox-home}"' in dev
    assert 'SWARM_ALLOW_NO_AUTH: "true"' not in base
