import argparse
import importlib
import asyncio
import os

def main():
    import os
    parser = argparse.ArgumentParser(description="Swarm CLI - Unified UX Blueprint Runner")
    parser.add_argument("blueprint", type=str, help="Blueprint to run (e.g., data_analysis)")
    parser.add_argument("--instruction", type=str, default="", help="Instruction or search query")
    parser.add_argument("--search_mode", type=str, choices=["code", "semantic"], default="semantic", help="Search mode")
    parser.add_argument("--test", action="store_true", help="Run in test mode (sets SWARM_TEST_MODE=1)")
    args = parser.parse_args()

    if args.test:
        os.environ["SWARM_TEST_MODE"] = "1"

    blueprint_module_name = f"src.swarm.blueprints.blueprint_{args.blueprint}"
    blueprint_class_name = f"{''.join([w.capitalize() for w in args.blueprint.split('_')])}Blueprint"
    try:
        module = importlib.import_module(blueprint_module_name)
        BlueprintClass = getattr(module, blueprint_class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"[CLI] Error: Could not find blueprint '{args.blueprint}'. {e}")
        return

    blueprint = BlueprintClass(blueprint_id=args.blueprint)
    messages = [{"role": "user", "content": args.instruction}]
    kwargs = {"search_mode": args.search_mode}

    async def run_blueprint():
        async for _ in blueprint.run(messages, **kwargs):
            pass

    if os.environ.get("SWARM_TEST_MODE"):
        asyncio.run(run_blueprint())
    else:
        print(f"[CLI] Would run blueprint: {args.blueprint} with instruction: '{args.instruction}' in {args.search_mode} mode.")

if __name__ == "__main__":
    main()
