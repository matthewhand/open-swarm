import argparse
import asyncio
from swarm.blueprints.poets.blueprint_poets import PoetsBlueprint

def main():
    parser = argparse.ArgumentParser(description="Poets: LLM creative code poetry assistant")
    parser.add_argument("--instruction", type=str, required=True, help="User instruction for Poets")
    args = parser.parse_args()
    bp = PoetsBlueprint(blueprint_id="cli")
    # Explicitly reload config after instantiation to avoid config access errors
    bp._load_configuration()
    async def run():
        messages = [{"role": "user", "content": args.instruction}]
        async for result in bp.run(messages):
            if isinstance(result, dict) and "messages" in result:
                content = result["messages"][0]["content"]
                print(content)
            else:
                print(result)
    asyncio.run(run())

if __name__ == "__main__":
    main()
