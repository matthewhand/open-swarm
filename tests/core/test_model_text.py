from swarm.core.model_text import is_usable_model_text, sanitize_model_text


def test_strips_unused50_spam():
    raw = "REST plan:\nFor<unused50><unused50><unused50>\n\nhi"
    assert sanitize_model_text(raw) == "REST plan:\nFor\n\nhi"


def test_empty_after_only_specials():
    assert sanitize_model_text("<unused50><unused50>") == ""
    assert sanitize_model_text("") == ""
    assert sanitize_model_text(None) == ""


def test_strips_ansi_and_esc_stripped_csi():
    raw = (
        "REST plan: anlı\x1b[13;28;13;1;0;1_"
        "\x1b[13;28;13;0;0;1_"
        "[13;28;13;1;0;1_[13;28;13;0;0;1_"
        "(no CLI agents configured — add a 'cli_agents' block; see docs/CLI_FUSION.md)"
    )
    cleaned = sanitize_model_text(raw)
    assert "13;28" not in cleaned
    assert "\x1b" not in cleaned
    assert "no CLI agents configured" in cleaned
    assert not is_usable_model_text("anlı[13;28;13;1;0;1_")
    assert is_usable_model_text("[rest-plan] solo")
