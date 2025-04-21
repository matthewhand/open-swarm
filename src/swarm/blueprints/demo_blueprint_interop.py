"""
Demo: Blueprint Interoperability via Agent-as-Tool Sharing

This script demonstrates how to instantiate two blueprints and share an agent/tool between them.
"""
from swarm.blueprints.family_ties.blueprint_family_ties import FamilyTiesBlueprint
from swarm.blueprints.zeus.blueprint_zeus import ZeusBlueprint

# Minimal stub for mcp_servers (no real MCPs for offline demo)
fake_mcp_servers = []

# Instantiate blueprints
family_ties = FamilyTiesBlueprint("family_ties")
zeus = ZeusBlueprint("zeus")

# Create entry agents for each blueprint
zeus_agent = zeus.create_starting_agent(mcp_servers=fake_mcp_servers)
family_agent = family_ties.create_starting_agent(mcp_servers=fake_mcp_servers)

# Register the FamilyTies agent as a tool for Zeus
zeus_agent.tools.append(
    family_agent.as_tool(
        tool_name="FamilySearchTool",
        tool_description="Search family data via Family Ties Blueprint"
    )
)

# Simulate a task delegated from Zeus to FamilySearchTool
instruction = "Find all cousins of Jane Doe born after 1950"

print("[INFO] Registered FamilyTies agent as a tool for Zeus agent.")
print("[INFO] Zeus agent tools:", [t.name for t in zeus_agent.tools])

print("\n[INFO] This demo shows how to compose blueprints via agent/tool sharing. See README for more.")
