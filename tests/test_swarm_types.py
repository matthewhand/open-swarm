import unittest
from swarm.types import Agent, Response, Result, Tool

def sample_tool_func(a, b):
    return a + b

class TestSwarmTypes(unittest.TestCase):
    def test_agent_defaults(self):
        agent = Agent()
        self.assertEqual(agent.name, "Agent")
        self.assertEqual(agent.model, "default")
        self.assertEqual(agent.instructions, "You are a helpful agent.")
        self.assertEqual(agent.functions, [])
        self.assertFalse(agent.parallel_tool_calls)

    def test_response_auto_id(self):
        response = Response(messages=[])
        self.assertTrue(response.id.startswith("response-"))
        self.assertEqual(response.messages, [])
        self.assertEqual(response.context_variables, {})

    def test_result_defaults(self):
        result = Result()
        self.assertEqual(result.value, "")
        self.assertIsNone(result.agent)
        self.assertEqual(result.context_variables, {})

    def test_tool_call(self):
        tool = Tool(name="sum", func=sample_tool_func, description="Adds two numbers")
        self.assertEqual(tool(2, 3), 5)
        self.assertEqual(tool.name, "sum")
        self.assertEqual(tool.description, "Adds two numbers")
        self.assertEqual(tool.input_schema, {})

if __name__ == "__main__":
    unittest.main()