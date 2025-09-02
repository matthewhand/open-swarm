import os
import json
import datetime as dt
from unittest.mock import patch

import pytest

from src.swarm.utils.general_utils import (
    serialize_datetime,
    custom_json_dumps,
    extract_chat_id,
)


class TestSerializeDatetime:
    def test_serialize_naive_datetime(self):
        d = dt.datetime(2024, 5, 17, 12, 34, 56)
        out = serialize_datetime(d)
        assert out == d.isoformat()

    def test_serialize_timezone_aware_datetime(self):
        tz = dt.timezone(dt.timedelta(hours=-7))
        d = dt.datetime(2024, 5, 17, 12, 34, 56, tzinfo=tz)
        out = serialize_datetime(d)
        # Expect ISO 8601 with offset
        assert out.endswith("-07:00")
        assert out.startswith("2024-05-17T12:34:56")

    def test_serialize_passthrough_string(self):
        s = "already-a-string"
        assert serialize_datetime(s) == s

    def test_serialize_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            serialize_datetime(object())


class TestCustomJsonDumps:
    def test_custom_json_dumps_uses_serializer(self):
        data = {"now": dt.datetime(2023, 1, 2, 3, 4, 5)}
        dumped = custom_json_dumps(data)
        loaded = json.loads(dumped)
        assert loaded["now"].startswith("2023-01-02T03:04:05")


class TestExtractChatId:
    @patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": ""}, clear=False)
    def test_extract_from_default_paths_simple_string(self):
        payload = {"metadata": {"channelInfo": {"channelId": "abc-123"}}}
        cid = extract_chat_id(payload)
        assert cid == "abc-123"

    @patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": ""}, clear=False)
    def test_extract_from_default_paths_dict_value(self):
        payload = {"metadata": {"userInfo": {"userId": "user-42"}}}
        # userId path is in defaults; ensure it extracts as string
        assert extract_chat_id(payload) == "user-42"

    @patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "metadata.userInfo.userId||metadata.channelInfo.channelId"})
    def test_extract_with_env_overrides_multiple_paths(self):
        payload = {"metadata": {"channelInfo": {"channelId": "chan-9"}}}
        # Should try userId first (not present), then channelId
        assert extract_chat_id(payload) == "chan-9"

    def test_extract_json_parse_special_case(self):
        # Matches the special-case path handled in implementation
        payload = {
            "messages": [
                {
                    "tool_calls": [
                        {"function": {"arguments": json.dumps({"chat_id": "from-json-args"})}}
                    ]
                }
            ]
        }
        # Ensure env path includes the json_parse expression to exercise code path
        path = "`json_parse(messages[-1].tool_calls[-1].function.arguments).chat_id`"
        with patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": path}, clear=False):
            assert extract_chat_id(payload) == "from-json-args"

    def test_extract_returns_empty_when_not_found(self):
        assert extract_chat_id({}) == ""
