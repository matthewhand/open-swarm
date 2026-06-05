# src/swarm/agent/agent.py

import json
from collections.abc import Callable
from typing import Any


class Agent:
    def __init__(self, name: str, instructions: str):
        self.name = name
        self.instructions = instructions
        self.tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, func: Callable[..., Any], description: str = ""):
        """
        Registers a tool with the agent.
        
        Args:
            name (str): Name of the tool.
            func (Callable[..., Any]): The function implementing the tool.
            description (str): Description of the tool.
        """
        self.tools[name] = {
            "func": func,
            "description": description
        }

    async def process(self, query: str) -> str:
        """
        Processes a user query by determining which tool to invoke.
        
        Args:
            query (str): The user's query in JSON format specifying the tool and arguments.
        
        Returns:
            str: The response from the tool execution.
        """
        try:
            request = json.loads(query)
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})
            if tool_name in self.tools:
                tool_func = self.tools[tool_name]["func"]
                result = await tool_func(**arguments)
                return result
            else:
                return f"Tool '{tool_name}' not found."
        except json.JSONDecodeError:
            return "Invalid query format. Expected JSON with 'tool' and 'arguments'."
        except Exception as e:
            return f"Error processing query: {e}"
