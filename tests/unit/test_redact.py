from swarm.utils.redact import redact_sensitive_data


def test_redact_sensitive_data_basic():
    data = {
        "api_key": "sk-1234567890abcdef",
        "password": "hunter2",
        "token": "tok-abcdef123456",
        "username": "notsecret",
        "nested": {
            "secret": "supersecret",
            "other": "value"
        },
        "list": [
            {"api_key": "sk-abcdef"},
            "nope"
        ]
    }
    redacted = redact_sensitive_data(data, reveal_chars=0)
    # API keys and tokens should be masked
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["username"] == "notsecret"
    assert redacted["nested"]["secret"] == "[REDACTED]"
    assert redacted["nested"]["other"] == "value"
    assert redacted["list"][0]["api_key"] == "[REDACTED]"
    assert redacted["list"][1] == "nope"

def test_redact_sensitive_data_string():
    s = "my api_key is sk-123456"
    assert redact_sensitive_data(s) == s  # strings not in dict/list are not redacted

def test_redact_sensitive_data_custom_keys():
    data = {"custom_secret": "shouldhide", "foo": "bar"}
    redacted = redact_sensitive_data(data, sensitive_keys=["custom_secret"], reveal_chars=4)
    assert redacted["custom_secret"].startswith("shou") and redacted["custom_secret"].endswith("hide")
    assert "[REDACTED]" in redacted["custom_secret"]
    assert redacted["foo"] == "bar"


def test_sensitive_keys_are_case_insensitive():
    redacted = redact_sensitive_data({"API_KEY": "sk-x", "Password": "p", "Secret": "s"})
    assert redacted["API_KEY"] == "[REDACTED]"
    assert redacted["Password"] == "[REDACTED]"
    assert redacted["Secret"] == "[REDACTED]"


def test_reveal_chars_short_value_is_fully_masked():
    # Too short to safely reveal head+tail -> fall back to a full mask.
    assert redact_sensitive_data({"token": "abc"}, reveal_chars=4)["token"] == "[REDACTED]"


def test_reveal_chars_partial_format():
    assert redact_sensitive_data({"token": "abcdefghij"}, reveal_chars=3)["token"] == "abc[REDACTED]hij"


def test_non_string_sensitive_value_is_masked():
    # A secret stored as a non-string must not leak through unmasked.
    assert redact_sensitive_data({"api_key": 12345})["api_key"] == "[REDACTED]"
    assert redact_sensitive_data({"password": True})["password"] == "[REDACTED]"


def test_sensitive_key_with_structured_value_is_masked():
    # A dict/list under a sensitive key must be masked wholesale, not passed through.
    assert redact_sensitive_data({"secret": {"inner": "leak"}})["secret"] == "[REDACTED]"
    assert redact_sensitive_data({"token": ["leak1", "leak2"]})["token"] == "[REDACTED]"


def test_env_style_keys_are_redacted_by_substring():
    """OPENAI_API_KEY / GITHUB_TOKEN style names embed sensitive tokens — must redact."""
    data = {
        "env": {
            "OPENAI_API_KEY": "sk-mcp-openai",
            "GITHUB_TOKEN": "ghp_xxx",
            "MONDAY_API_KEY": "mon_xxx",
            "NORMAL_PATH": "/usr/bin/npx",
        }
    }
    redacted = redact_sensitive_data(data, mask="***HIDDEN***")
    assert redacted["env"]["OPENAI_API_KEY"] == "***HIDDEN***"
    assert redacted["env"]["GITHUB_TOKEN"] == "***HIDDEN***"
    assert redacted["env"]["MONDAY_API_KEY"] == "***HIDDEN***"
    assert redacted["env"]["NORMAL_PATH"] == "/usr/bin/npx"


def test_is_sensitive_key_helper():
    from swarm.utils.redact import is_sensitive_key

    assert is_sensitive_key("api_key")
    assert is_sensitive_key("OPENAI_API_KEY")
    assert is_sensitive_key("github-token")
    assert is_sensitive_key("client_secret")
    assert is_sensitive_key("not_secret")  # segment "secret"
    assert not is_sensitive_key("model")
    assert not is_sensitive_key("base_url")
    assert not is_sensitive_key("mytokenized")  # no underscore boundary
