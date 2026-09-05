"""Fixture: three openai-agents personas (REQ-81). Never executed by the parser."""

from agents import Agent

researcher = Agent(name="Researcher", instructions="Look things up.")
writer = Agent(name="Writer", instructions="Draft the answer.")
reviewer = Agent(name="Reviewer", instructions="Check the draft.")
