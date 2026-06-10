import datetime
import json
import uuid
import pytest
from swarm.utils.general_utils import custom_json_dumps, swarm_json_serializer

class TestCustomJsonDumps:
    def test_basic_types(self):
        data = {"a": 1, "b": "string", "c": [1, 2, 3], "d": True, "e": None}
        result = custom_json_dumps(data)
        assert json.loads(result) == data

    def test_datetime_serialization(self):
        dt = datetime.datetime(2023, 10, 27, 12, 30, 45)
        data = {"timestamp": dt}
        result = custom_json_dumps(data)
        assert json.loads(result) == {"timestamp": dt.isoformat()}

    def test_date_serialization(self):
        d = datetime.date(2023, 10, 27)
        data = {"date": d}
        result = custom_json_dumps(data)
        assert json.loads(result) == {"date": d.isoformat()}

    def test_uuid_serialization(self):
        u = uuid.uuid4()
        data = {"id": u}
        result = custom_json_dumps(data)
        assert json.loads(result) == {"id": str(u)}

    def test_nested_structure(self):
        dt = datetime.datetime(2023, 10, 27, 12, 0, 0)
        u = uuid.uuid4()
        data = {
            "meta": {
                "created_at": dt,
                "uid": u
            },
            "items": [
                {"id": uuid.uuid4(), "val": 1},
                {"id": uuid.uuid4(), "val": 2}
            ]
        }
        result = custom_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["meta"]["created_at"] == dt.isoformat()
        assert parsed["meta"]["uid"] == str(u)
        assert len(parsed["items"]) == 2
        assert isinstance(parsed["items"][0]["id"], str)

    def test_json_kwargs(self):
        data = {"b": 2, "a": 1}
        # Test sort_keys
        result_sorted = custom_json_dumps(data, sort_keys=True)
        assert result_sorted == '{"a": 1, "b": 2}'

        # Test indent
        result_indent = custom_json_dumps(data, indent=2, sort_keys=True)
        assert result_indent == '{\n  "a": 1,\n  "b": 2\n}'

    def test_unsupported_type(self):
        class Unsupported:
            pass

        data = {"obj": Unsupported()}
        with pytest.raises(TypeError) as excinfo:
            custom_json_dumps(data)
        assert "not serializable" in str(excinfo.value)

class TestSwarmJsonSerializer:
    def test_serializer_directly_datetime(self):
        dt = datetime.datetime(2023, 1, 1)
        assert swarm_json_serializer(dt) == dt.isoformat()

    def test_serializer_directly_uuid(self):
        u = uuid.uuid4()
        assert swarm_json_serializer(u) == str(u)

    def test_serializer_raises_type_error(self):
        with pytest.raises(TypeError):
            swarm_json_serializer(set([1, 2]))
