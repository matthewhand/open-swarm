import asyncio
import json
import os
from src.swarm.blueprints.codey.blueprint_codey import CodeyBlueprint
from src.swarm.blueprints.digitalbutlers.blueprint_digitalbutlers import DigitalButlersBlueprint
from src.swarm.blueprints.mcp_demo.blueprint_mcp_demo import MCPDemoBlueprint
from src.swarm.blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint
from src.swarm.blueprints.suggestion.blueprint_suggestion import SuggestionBlueprint

REPORT = []

async def integration_scenario():
    """
    Scenario: Codey generates code, DigitalButlers reviews, MCP Demo analyzes, Suggestion proposes improvement, EchoCraft echoes final result.
    """
    codey = CodeyBlueprint(blueprint_id="test_codey")
    digitalbutlers = DigitalButlersBlueprint(blueprint_id="test_butlers")
    mcp_demo = MCPDemoBlueprint(blueprint_id="test_mcp")
    suggestion = SuggestionBlueprint(blueprint_id="test_suggestion")
    echocraft = EchoCraftBlueprint(blueprint_id="test_echocraft")

    # Step 1: Codey generates code
    messages = [{"role": "user", "content": "Write a function that adds two numbers in Python."}]
    codey_result = None
    async for result in codey.run(messages):
        codey_result = result
    REPORT.append({"step": "Codey generates code", "result": str(codey_result)})

    # Step 2: DigitalButlers reviews code
    review_messages = [{"role": "user", "content": f"Review this code: {codey_result}"}]
    butlers_result = None
    async for result in digitalbutlers.run(review_messages):
        butlers_result = result
    REPORT.append({"step": "DigitalButlers reviews code", "result": str(butlers_result)})

    # Step 3: MCP Demo analyzes
    analyze_messages = [{"role": "user", "content": f"Analyze this review: {butlers_result}"}]
    mcp_result = None
    async for result in mcp_demo.run(analyze_messages):
        mcp_result = result
    REPORT.append({"step": "MCP Demo analyzes", "result": str(mcp_result)})

    # Step 4: Suggestion proposes improvement
    suggestion_messages = [{"role": "user", "content": f"Suggest improvements based on: {mcp_result}"}]
    suggestion_result = None
    async for result in suggestion.run(suggestion_messages):
        suggestion_result = result
    REPORT.append({"step": "Suggestion proposes improvement", "result": str(suggestion_result)})

    # Step 5: EchoCraft echoes final suggestion
    echo_messages = [{"role": "user", "content": f"Echo this suggestion: {suggestion_result}"}]
    echo_result = None
    async for result in echocraft.run(echo_messages):
        echo_result = result
    REPORT.append({"step": "EchoCraft echoes", "result": str(echo_result)})

async def stress_test_parallel():
    """
    Stress test: Launch 10 parallel Codey code generations and reviews.
    """
    codey = CodeyBlueprint(blueprint_id="test_codey_parallel")
    digitalbutlers = DigitalButlersBlueprint(blueprint_id="test_butlers_parallel")
    tasks = []
    for i in range(10):
        msg = [{"role": "user", "content": f"Write a function that returns {i} squared."}]
        tasks.append(codey.run(msg))
    codey_results = []
    for coro in tasks:
        result = None
        async for r in coro:
            result = r
        codey_results.append(result)
    REPORT.append({"step": "Parallel Codey generations", "result": str(codey_results)})
    # Review in parallel
    review_tasks = []
    for code in codey_results:
        review_tasks.append(digitalbutlers.run([{"role": "user", "content": f"Review: {code}"}]))
    butlers_results = []
    for coro in review_tasks:
        result = None
        async for r in coro:
            result = r
        butlers_results.append(result)
    REPORT.append({"step": "Parallel DigitalButlers reviews", "result": str(butlers_results)})

async def main():
    await integration_scenario()
    await stress_test_parallel()
    # Write results
    with open("swarm_integration_report.json", "w") as f:
        json.dump(REPORT, f, indent=2)
    print("\n\033[92m\u2728 SWARM INTEGRATION TEST COMPLETE! See swarm_integration_report.json for details.\033[0m\n")

if __name__ == "__main__":
    asyncio.run(main())
