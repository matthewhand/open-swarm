"""Run the same inventory blueprint used by the HTTP API."""
import argparse
import asyncio
import os
import sys

from swarm.blueprints.inventory_demo.blueprint_inventory_demo import (
    InventoryDemoBlueprint,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", default="What should we reorder, and what will it cost?")
    args = parser.parse_args()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
    import django
    django.setup()

    async def run():
        blueprint = InventoryDemoBlueprint(blueprint_id="inventory_demo")
        async for chunk in blueprint.run([{"role": "user", "content": args.message}]):
            for message in chunk.get("messages", []):
                print(message.get("content", ""))
            if chunk.get("error"):
                return 1
        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
