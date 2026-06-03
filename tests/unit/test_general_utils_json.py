import datetime
import json
import pytest
from src.swarm.utils.general_utils import serialize_datetime, custom_json_dumps

class TestSerializeDatetime:
    def test_serialize_datetime_obj(self):
        dt = datetime.datetime(2023, 10, 27, 12, 0, 0)
        assert serialize_datetime(dt) == "2023-10-27T12:00:00"

    def test_serialize_string(self):
        s = "2023-10-27T12:00:00"
        assert serialize_datetime(s) == s

    def test_serialize_unsupported_type(self):
        with pytest.raises(TypeError) as excinfo:
            serialize_datetime(123)
        assert "Type <class 'int'> not serializable" in str(excinfo.value)

class TestCustomJsonDumps:
    def test_dumps_basic(self):
        data = {"key": "value"}
        assert custom_json_dumps(data) == json.dumps(data)

    def test_dumps_with_datetime(self):
        dt = datetime.datetime(2023, 10, 27, 12, 0, 0)
        data = {"time": dt}
        expected = json.dumps({"time": "2023-10-27T12:00:00"})
        assert custom_json_dumps(data) == expected

    def test_dumps_with_nested_datetime(self):
        dt = datetime.datetime(2023, 10, 27, 12, 0, 0)
        data = {"outer": {"inner": dt}}
        expected = json.dumps({"outer": {"inner": "2023-10-27T12:00:00"}})
        assert custom_json_dumps(data) == expected

    def test_dumps_with_kwargs(self):
        data = {"a": 1, "b": 2}
        # indent=4 is a kwarg passed to json.dumps
        result = custom_json_dumps(data, indent=4)
        assert result == json.dumps(data, indent=4)
        assert "\n    " in result

    def test_dumps_raises_type_error_for_unsupported(self):
        data = {"set": {1, 2, 3}}
        with pytest.raises(TypeError):
            custom_json_dumps(data)
