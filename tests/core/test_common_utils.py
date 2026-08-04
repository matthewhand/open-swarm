import pytest
from swarm.core.common_utils import get_agent_name

def test_get_agent_name_with_name_attr():
    class Agent:
        name = "TestAgent"

    assert get_agent_name(Agent()) == "TestAgent"

def test_get_agent_name_with_name_instance_attr():
    class Agent:
        def __init__(self, name):
            self.name = name

    assert get_agent_name(Agent("InstanceAgent")) == "InstanceAgent"

def test_get_agent_name_with_only_underscore_name():
    class Agent:
        pass

    # Classes have __name__ by default
    assert get_agent_name(Agent) == "Agent"

def test_get_agent_name_precedence():
    class Agent:
        name = "NameAttr"

    # Agent.__name__ is "Agent"
    assert get_agent_name(Agent) == "NameAttr"

def test_get_agent_name_unknown():
    class Agent:
        pass

    agent = Agent()
    # Instances don't have __name__ or name by default
    assert not hasattr(agent, "name")
    assert not hasattr(agent, "__name__")

    assert get_agent_name(agent) == "<unknown>"

def test_get_agent_name_none():
    # None doesn't have name or __name__
    assert get_agent_name(None) == "<unknown>"

def test_get_agent_name_with_function():
    def my_agent():
        pass

    assert get_agent_name(my_agent) == "my_agent"

def test_get_agent_name_basic_types():
    assert get_agent_name("string") == "<unknown>"
    assert get_agent_name(123) == "<unknown>"
    assert get_agent_name([]) == "<unknown>"
