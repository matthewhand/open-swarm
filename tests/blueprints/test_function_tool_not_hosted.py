"""Regression guard: blueprint file/shell tools must be real SDK FunctionTools.

These blueprints previously wrapped their tools in a local ``PatchedFunctionTool``
stub that the openai-agents SDK did not recognize, so the ChatCompletions path
mis-flagged them as *hosted* tools and raised "Hosted tools are not supported
with the ChatCompletions API" — breaking jeeves/poets/rue_code on any non-OpenAI
backend. They must be `agents.FunctionTool` instances.
"""

from __future__ import annotations

from agents import FunctionTool

from swarm.blueprints.jeeves import blueprint_jeeves as jeeves
from swarm.blueprints.poets import blueprint_poets as poets
from swarm.blueprints.rue_code import blueprint_rue_code as rue


def test_jeeves_tools_are_function_tools():
    for t in (jeeves.read_file_tool, jeeves.write_file_tool, jeeves.list_files_tool, jeeves.execute_shell_command_tool):
        assert isinstance(t, FunctionTool)


def test_poets_tools_are_function_tools():
    for t in (poets.read_file_tool, poets.write_file_tool, poets.list_files_tool, poets.execute_shell_command_tool):
        assert isinstance(t, FunctionTool)


def test_rue_code_tools_are_function_tools():
    for t in (rue.read_file_tool, rue.write_file_tool, rue.list_files_tool, rue.execute_shell_command_tool, rue.llm_cost_tool_fn):
        assert isinstance(t, FunctionTool)
