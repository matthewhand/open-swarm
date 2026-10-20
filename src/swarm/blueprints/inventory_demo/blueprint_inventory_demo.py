"""Read-only, bounded tool example for the CLI and chat-completions API."""
from typing import Any, ClassVar

from agents import Agent, function_tool

from swarm.core.kind_bases import ApiKindBase


def stock_report() -> dict[str, Any]:
    """Calculate reorder quantities from the bundled fictional inventory."""
    items = [
        {"sku": "notebooks", "on_hand": 3, "target": 12, "unit_cost": 4},
        {"sku": "pens", "on_hand": 20, "target": 10, "unit_cost": 2},
        {"sku": "folders", "on_hand": 2, "target": 8, "unit_cost": 3},
    ]
    orders = []
    for item in items:
        quantity = max(0, item["target"] - item["on_hand"])
        if quantity:
            orders.append({"sku": item["sku"], "quantity": quantity,
                           "cost": quantity * item["unit_cost"]})
    return {"fictional_data": True, "orders": orders,
            "total_cost": sum(item["cost"] for item in orders)}


class InventoryDemoBlueprint(ApiKindBase):
    metadata: ClassVar[dict[str, Any]] = {
        "name": "inventory_demo",
        "title": "Inventory reorder example",
        "description": "Read-only tool workflow over bundled fictional stock.",
        "version": "1.0.0",
        "required_mcp_servers": [],
        "env_vars": [],
    }

    def create_starting_agent(self, mcp_servers=None):
        return Agent(
            name="inventory_demo",
            instructions=("Always call stock_report before answering inventory questions. "
                          "Use its calculated quantities and total cost. Explain that the "
                          "inventory is fictional. Never claim to place orders."),
            model=self._get_model_instance(self.llm_profile_name),
            tools=[function_tool(stock_report)],
            mcp_servers=list(mcp_servers or []),
        )
