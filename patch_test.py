with open("tests/api/test_cli_fusion_api.py", "r") as f:
    text = f.read()

text = text.replace('def test_moa_panel_synthesizes_over_api', 'def test_cli_fusion_panel_synthesizes_over_api')
text = text.replace('def test_moa_uses_default_preset_without_params', 'def test_cli_fusion_uses_default_preset_without_params')
text = text.replace('def test_system_fingerprint_names_resolved_backends_x', 'def test_system_fingerprint_names_resolved_backends')
text = text.replace('_post(client, "moa",', '_post(client, "cli_fusion",')
text = text.replace('assert fp.startswith("moa:")', 'assert fp.startswith("cli_fusion:")')

with open("tests/api/test_cli_fusion_api.py", "w") as f:
    f.write(text)
