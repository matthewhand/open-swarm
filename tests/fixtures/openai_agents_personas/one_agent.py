"""Fixture: one openai-agents persona (REQ-81). Never executed by the parser."""

from agents import Agent

solo = Agent(name="Solo", instructions="Work alone.")
