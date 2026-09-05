"""software-dev / Chatty style helpers — names are first positional strings."""


class SoftwareDevLike:
    def _build_agents(self):
        engineer = self._make_agent(
            "engineer",
            "Implement to Success.",
            [],
        )
        skeptic = self._make_agent(
            "skeptic",
            "Look-only PASS/FAIL.",
            [],
        )
        cos = self._make_agent(
            "coding-requirements-gate",
            "Quote Intent/Success/Constraints/Owner.",
            [],
        )
        if hasattr(engineer, "as_tool"):
            cos.tools.append(engineer.as_tool(tool_name="consult_engineer"))
        if hasattr(skeptic, "as_tool"):
            cos.tools.append(skeptic.as_tool(tool_name="consult_skeptic"))
        return engineer, skeptic, cos

    def _make_agent(self, name, instructions, tools):
        return None
