import pytest
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint

def test_inject_feedback():
    blueprint = CodeyBlueprint(blueprint_id="test-feedback")
    # Feedback/correction message
    messages = [
        {"role": "user", "content": "That is wrong. Try again with file foo.py instead."},
        {"role": "user", "content": "What is the result?"}
    ]
    injected = blueprint.test_inject_feedback()
    sys_msgs = [m for m in injected if m["role"] == "system"]
    assert any("FEEDBACK" in m["content"] for m in sys_msgs)
    # Negative test: no feedback in message
    messages2 = [
        {"role": "user", "content": "Show me the result."}
    ]
    injected2 = blueprint._inject_feedback(messages2.copy())
    sys_msgs2 = [m for m in injected2 if m["role"] == "system"]
    assert not any("FEEDBACK" in m["content"] for m in sys_msgs2)
